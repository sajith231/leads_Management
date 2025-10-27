from django.apps import AppConfig


class PurchaseOrderConfig(AppConfig):
    """
    Configuration for Purchase Order Application
    This handles both Supplier Master and Purchase Order modules
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchase_order'
    verbose_name = 'Purchase Order Management'
    
    def ready(self):
        """
        Import signals or perform startup tasks here if needed
        """
        pass
