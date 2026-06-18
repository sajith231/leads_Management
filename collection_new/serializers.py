from rest_framework import serializers
from .models import Collection


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
            'notes',
            'status',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            # payment_proof accepts file upload but is NOT write_only
            # so payment_proof_url is populated in the response
            'payment_proof': {'required': False},
        }

    def get_created_by_name(self, obj):
        if obj.created_by:
            full = obj.created_by.get_full_name()
            return full if full else obj.created_by.username
        return None

    def get_payment_proof_url(self, obj):
        if obj.payment_proof:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_proof.url)
            return obj.payment_proof.url
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