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