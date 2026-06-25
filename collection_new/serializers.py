from rest_framework import serializers
from .models import Collection
from common.cloudflare_storage import upload_to_cloudflare, extract_file_key_from_url


class CollectionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    collection_type_display = serializers.CharField(
        source='get_collection_type_display', read_only=True
    )
    payment_proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            'id',
            'company',
            'department',
            'client_name',
            'collection_type',
            'collection_type_display',
            'amount',
            'paid_for',
            'payment_proof',
            'payment_proof_url',
            'cloudflare_r2_url',
            'notes',
            'status',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'updated_at', 'cloudflare_r2_url']
        extra_kwargs = {
            'payment_proof': {'required': False},
        }

    def get_created_by_name(self, obj):
        if obj.created_by:
            full = obj.created_by.get_full_name()
            return full if full else obj.created_by.username
        return None

    def get_payment_proof_url(self, obj):
        """
        Return the Cloudflare R2 URL (primary source now that we only save to R2).
        """
        if obj.cloudflare_r2_url:
            return obj.cloudflare_r2_url
        return None

    def to_internal_value(self, data):
        """
        If payment_proof is submitted as a multi-file field (e.g. from Postman
        with 2 files selected), take only the first file so validation passes.

        QueryDict.copy() returns an *immutable* copy by default; calling
        setlist() on it is silently ignored (the change never sticks).
        We must build a brand-new mutable MultiValueDict so setlist works.
        """
        if hasattr(data, 'getlist'):
            files = data.getlist('payment_proof')
            if len(files) > 1:
                from django.utils.datastructures import MultiValueDict
                # Rebuild as a fresh mutable MultiValueDict
                new_data = MultiValueDict()
                for key in data:
                    if key == 'payment_proof':
                        continue
                    new_data.setlist(key, data.getlist(key))
                # Keep only the first file
                new_data.setlist('payment_proof', [files[0]])
                data = new_data
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Mirror the form's proof-required logic."""
        PROOF_REQUIRED = ('cheque', 'upi', 'bank_transfer')
        ctype = attrs.get('collection_type', '')
        proof = attrs.get('payment_proof', None)

        # On create: proof must be present for certain types
        if self.instance is None:
            if ctype in PROOF_REQUIRED and not proof:
                raise serializers.ValidationError({
                    'payment_proof': f'Payment proof is required for {ctype.replace("_", " ").title()}.'
                })

        # On update: allow no new file if one already exists
        if self.instance is not None:
            if ctype in PROOF_REQUIRED and not proof and not self.instance.payment_proof:
                raise serializers.ValidationError({
                    'payment_proof': f'Payment proof is required for {ctype.replace("_", " ").title()}.'
                })

        return attrs

    def create(self, validated_data):
        """Create instance and upload file to Cloudflare R2 if present (don't save locally)."""
        payment_proof = validated_data.pop('payment_proof', None)
        instance = Collection.objects.create(**validated_data)
        
        # Upload to Cloudflare R2 if file provided
        if payment_proof:
            self._upload_to_cloudflare(instance, payment_proof)
            # Don't save payment_proof locally; persist all R2 fields together
            instance.payment_proof = None
            instance.save(update_fields=['payment_proof', 'cloudflare_r2_url', 'cloudflare_r2_key'])
        
        return instance

    def update(self, instance, validated_data):
        """Update instance and upload new file to Cloudflare R2 if provided (don't save locally)."""
        payment_proof = validated_data.pop('payment_proof', None)
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # If new file provided, delete old R2 file and upload new one
        if payment_proof:
            # Delete old R2 file if exists
            if instance.cloudflare_r2_key:
                from common.cloudflare_storage import delete_from_cloudflare
                delete_from_cloudflare(instance.cloudflare_r2_key)
            
            self._upload_to_cloudflare(instance, payment_proof)
            # Don't save payment_proof locally
            instance.payment_proof = None
        
        instance.save()
        return instance

    def _upload_to_cloudflare(self, instance, file_obj):
        """Helper method to upload file to Cloudflare R2 and persist the R2 fields."""
        result = upload_to_cloudflare(file_obj, folder_name='collection_proofs')

        if result['success']:
            instance.cloudflare_r2_url = result['r2_url']
            instance.cloudflare_r2_key = result['file_key']
            instance.save(update_fields=['cloudflare_r2_url', 'cloudflare_r2_key'])
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to upload file to Cloudflare R2: {result['error']}")