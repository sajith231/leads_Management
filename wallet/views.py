from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Wallet
from urllib.parse import quote

def wallet_list(request):
    # Get all wallets for display
    wallets = Wallet.objects.all().order_by('-created_at')
    
    # Group wallets by upload type for ribbon counts
    bank_wallets = Wallet.objects.filter(upload_type='bank')
    qr_wallets = Wallet.objects.filter(upload_type='qr')
    document_wallets = Wallet.objects.filter(upload_type='document')
    other_wallets = Wallet.objects.filter(upload_type='other')
    
    context = {
        'wallets': wallets,
        'bank_wallets': bank_wallets,
        'qr_wallets': qr_wallets,
        'document_wallets': document_wallets,
        'other_wallets': other_wallets,
    }
    
    return render(request, 'wallet_list.html', context)

def add_wallet(request):
    if request.method == 'POST':
        # Get common form data
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')
        
        # Basic validation - only title, upload_type, and visibility are required
        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields (Title, Upload Type, Visibility).')
            return render(request, 'add_wallet.html')
        
        # Validate image if provided
        if image:
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = image.name.split('.')[-1].lower()
            
            if file_extension not in allowed_extensions:
                messages.error(request, 'Only JPG, JPEG, and PNG images are allowed.')
                return render(request, 'add_wallet.html')
            
            # Validate file size (5MB max)
            if image.size > 5 * 1024 * 1024:
                messages.error(request, 'Image file size should not exceed 5MB.')
                return render(request, 'add_wallet.html')
        
        # Create wallet object
        wallet = Wallet(
            title=title,
            upload_type=upload_type,
            visibility_priority=visibility_priority,
            description=description,
            image=image
        )
        
        # Handle type-specific fields (all optional now)
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '')
            wallet.bank_address = request.POST.get('bank_address', '')
        
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
        
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')
        
        if request.user.is_authenticated:
            wallet.created_by = request.user
        
        wallet.save()
        messages.success(request, 'Wallet item added successfully!')
        return redirect('wallet_list')
    
    return render(request, 'add_wallet.html')

def edit_wallet(request, wallet_id):
    """
    Edit existing wallet. GET -> show form prefilled.
    POST -> validate and save updates (including optional new image upload).
    """
    wallet = get_object_or_404(Wallet, id=wallet_id)

    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        # Basic required validation
        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields (Title, Upload Type, Visibility).')
            return render(request, 'edit_wallet.html', {'wallet': wallet})

        # Decide which file input might be present depending on upload_type
        new_image = None
        # these names match the inputs used in your add/edit templates
        # prefer type-specific file input names (same as add_wallet.html)
        # check all possible file inputs and pick the one uploaded (if any)
        for fkey in ('image_bank', 'image_qr', 'image_document', 'image_other', 'image'):
            if fkey in request.FILES:
                new_image = request.FILES[fkey]
                break

        # Validate new image if provided
        if new_image:
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = new_image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                messages.error(request, 'Only JPG, JPEG, and PNG images are allowed.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})

            if new_image.size > 5 * 1024 * 1024:
                messages.error(request, 'Image file size should not exceed 5MB.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})

        # Update wallet fields
        wallet.title = title
        wallet.upload_type = upload_type
        wallet.visibility_priority = visibility_priority
        wallet.description = description

        # update type-specific fields
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '')
            wallet.bank_address = request.POST.get('bank_address', '')
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
            # clear bank/other fields (optional)
            wallet.account_holder_name = wallet.account_number = wallet.ifsc_code = wallet.bank_address = ''
            wallet.other_name = ''
        elif upload_type == 'document':
            # document doesn't have specific text fields in your template
            wallet.account_holder_name = wallet.account_number = wallet.ifsc_code = wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')
            wallet.account_holder_name = wallet.account_number = wallet.ifsc_code = wallet.bank_address = ''
            wallet.qr_name = ''

        # Replace image if new image uploaded
        if new_image:
            # Optionally delete old file from storage (if desired and exists)
            try:
                if wallet.image and wallet.image.name:
                    old_path = wallet.image.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception:
                # if storage backend is not file-based, skip deletion
                pass

            wallet.image = new_image  # Django FileField handles saving on wallet.save()

        # set modified_by if you have such field - or keep created_by untouched
        if request.user.is_authenticated:
            # optionally track last edited user
            try:
                wallet.modified_by = request.user
            except Exception:
                pass

        wallet.save()
        messages.success(request, 'Wallet item updated successfully!')
        return redirect('wallet_list')

    # GET: show edit form with wallet object
    return render(request, 'edit_wallet.html', {'wallet': wallet})

def delete_wallet(request, wallet_id):
    if request.method == 'POST':
        try:
            wallet = Wallet.objects.get(id=wallet_id)
            wallet.delete()
            messages.success(request, 'Wallet item deleted successfully!')
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet item not found.')
    
    return redirect('wallet_list')

def wallet_detail(request, wallet_id):
    """API endpoint to get wallet details for popup"""
    wallet = get_object_or_404(Wallet, id=wallet_id)
    
    data = {
        'id': wallet.id,
        'title': wallet.title,
        'upload_type': wallet.get_upload_type_display(),
        'upload_type_code': wallet.upload_type,
        'visibility_priority': wallet.get_visibility_priority_display(),
        'description': wallet.description,
        'image_url': wallet.image.url if wallet.image else None,
        'created_at': wallet.created_at.strftime('%B %d, %Y at %I:%M %p'),
        'created_by': wallet.created_by.username if wallet.created_by else 'Anonymous',
    }
    
    # Add type-specific fields
    if wallet.upload_type == 'bank':
        data['account_holder_name'] = wallet.account_holder_name
        data['account_number'] = wallet.account_number
        data['ifsc_code'] = wallet.ifsc_code
        data['bank_address'] = wallet.bank_address
    elif wallet.upload_type == 'qr':
        data['qr_name'] = wallet.qr_name
    elif wallet.upload_type == 'other':
        data['other_name'] = wallet.other_name
    
    return JsonResponse(data)

def wallet_whatsapp_share(request, wallet_id):
    """Generate WhatsApp share message for wallet details"""
    wallet = get_object_or_404(Wallet, id=wallet_id)
    
    # Build the message
    message = f"*{wallet.title}*\n\n"
    message += f"📋 Type: {wallet.get_upload_type_display()}\n"
    
    # Add type-specific details
    if wallet.upload_type == 'bank':
        message += "\n💳 *Bank Details:*\n"
        if wallet.account_holder_name:
            message += f"Account Holder: {wallet.account_holder_name}\n"
        if wallet.account_number:
            message += f"Account Number: {wallet.account_number}\n"
        if wallet.ifsc_code:
            message += f"IFSC Code: {wallet.ifsc_code}\n"
        if wallet.bank_address:
            message += f"Bank Address: {wallet.bank_address}\n"
    
    elif wallet.upload_type == 'qr':
        if wallet.qr_name:
            message += f"\n📱 QR Name: {wallet.qr_name}\n"
    
    elif wallet.upload_type == 'other':
        if wallet.other_name:
            message += f"\n👝 Wallet Name: {wallet.other_name}\n"
    
    if wallet.description:
        message += f"\n📝 Description: {wallet.description}\n"
    
    # Add view link
    detail_url = request.build_absolute_uri(f'/wallet/detail/{wallet_id}/')
    message += f"\n🔗 View Details: {detail_url}"
    
    # URL encode the message
    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"
    
    return JsonResponse({'whatsapp_url': whatsapp_url, 'message': message})