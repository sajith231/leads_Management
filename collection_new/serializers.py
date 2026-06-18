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
            # Don't save payment_proof locally
            instance.payment_proof = None
            instance.save(update_fields=['payment_proof'])
        
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
        """Helper method to upload file to Cloudflare R2."""
        result = upload_to_cloudflare(file_obj, folder_name='collection_proofs')
        
        if result['success']:
            instance.cloudflare_r2_url = result['r2_url']
            instance.cloudflare_r2_key = result['file_key']
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to upload file to Cloudflare R2: {result['error']}")