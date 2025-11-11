# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Wallet
from urllib.parse import quote
import os
from django.db.models import Q

def is_admin_user(request):
    """
    Determine whether the current request should be treated as admin/superadmin.
    Checks:
      - Django superuser flag (request.user.is_superuser)
      - a session variable 'user_level' (your app stores this at login)
    Adapt the admin_levels list if your app uses different strings.
    """
    try:
        if request.user and getattr(request.user, 'is_superuser', False):
            return True
    except Exception:
        pass

    user_level = request.session.get('user_level', '')
    admin_levels = ['admin_level', '5level', '4level', 'superadmin', 'admin']
    return str(user_level) in admin_levels


def wallet_list(request):
    """Display wallets with role-based filtering.

    - Admins / superusers see ALL wallets.
    - Normal users see wallets where:
        * visibility_priority == 'user'
        OR
        * they are the creator (created_by matches request.user or session custom_user_id)
    """
    if is_admin_user(request):
        wallets = Wallet.objects.all().order_by('-created_at')
    else:
        # Owner filter: prefer Django user; fallback to custom session id 'custom_user_id' if present
        owner_q = Q()
        if request.user and request.user.is_authenticated:
            owner_q = Q(created_by=request.user)

        custom_user_id = request.session.get('custom_user_id')
        if custom_user_id:
            # include created_by id match as fallback
            owner_q = owner_q | Q(created_by__id=custom_user_id)

        user_visibility_q = Q(visibility_priority='user')

        wallets = Wallet.objects.filter(user_visibility_q | owner_q).order_by('-created_at')

    # Recompute type-specific lists from filtered wallets (so counts/sections reflect visibility)
    bank_wallets = wallets.filter(upload_type='bank')
    qr_wallets = wallets.filter(upload_type='qr')
    document_wallets = wallets.filter(upload_type='document')
    other_wallets = wallets.filter(upload_type='other')

    context = {
        'wallets': wallets,
        'bank_wallets': bank_wallets,
        'qr_wallets': qr_wallets,
        'document_wallets': document_wallets,
        'other_wallets': other_wallets,
    }

    return render(request, 'wallet_list.html', context)


def add_wallet(request):
    """Add new wallet item"""
    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        # Get the appropriate image field based on upload type
        image = None
        if upload_type == 'bank':
            image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            image = request.FILES.get('image_document')
        elif upload_type == 'other':
            image = request.FILES.get('image_other')

        # Basic validation
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

        # Handle type-specific fields
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
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
    """Edit existing wallet with permission guard (admin OR owner)."""
    wallet = get_object_or_404(Wallet, id=wallet_id)

    # Permission check: allow if admin OR owner
    allowed = False
    if is_admin_user(request):
        allowed = True
    else:
        # Owner via Django user
        if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
            allowed = True
        # Owner via custom session id
        custom_user_id = request.session.get('custom_user_id')
        if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
            try:
                if int(custom_user_id) == int(wallet.created_by.id):
                    allowed = True
            except Exception:
                pass

    if not allowed:
        messages.error(request, 'You do not have permission to edit this wallet.')
        return redirect('wallet_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'edit_wallet.html', {'wallet': wallet})

        # Get new image based on upload type
        new_image = None
        if upload_type == 'bank':
            new_image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            new_image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            new_image = request.FILES.get('image_document')
        elif upload_type == 'other':
            new_image = request.FILES.get('image_other')

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

        # Update type-specific fields
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
            wallet.bank_address = request.POST.get('bank_address', '')
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.other_name = ''
        elif upload_type == 'document':
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''

        # Replace image if new image uploaded
        if new_image:
            try:
                if wallet.image and hasattr(wallet.image, 'path'):
                    old_path = wallet.image.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception:
                pass
            wallet.image = new_image

        wallet.save()
        messages.success(request, 'Wallet item updated successfully!')
        return redirect('wallet_list')

    return render(request, 'edit_wallet.html', {'wallet': wallet})


def delete_wallet(request, wallet_id):
    """Delete wallet item with permission guard (admin OR owner)."""
    # Only proceed if POST; otherwise redirect back
    if request.method == 'POST':
        try:
            wallet = Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet item not found.')
            return redirect('wallet_list')

        # Permission check
        allowed = False
        if is_admin_user(request):
            allowed = True
        else:
            if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
                allowed = True
            custom_user_id = request.session.get('custom_user_id')
            if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
                try:
                    if int(custom_user_id) == int(wallet.created_by.id):
                        allowed = True
                except Exception:
                    pass

        if not allowed:
            messages.error(request, 'You do not have permission to delete this wallet.')
            return redirect('wallet_list')

        # Delete image file if exists
        try:
            if wallet.image and hasattr(wallet.image, 'path'):
                if os.path.exists(wallet.image.path):
                    os.remove(wallet.image.path)
        except Exception:
            pass

        wallet.delete()
        messages.success(request, 'Wallet item deleted successfully!')

    return redirect('wallet_list')


def wallet_whatsapp_share(request, wallet_id):
    """Generate WhatsApp share link with complete wallet details"""
    wallet = get_object_or_404(Wallet, id=wallet_id)

    # Build detailed message
    message = f"*{wallet.title}*\n\n"
    message += f"📋 Type: {wallet.get_upload_type_display()}\n"

    # Add type-specific details
    if wallet.upload_type == 'bank':
        message += "\n💳 *Bank Details:*\n"
        if wallet.account_holder_name:
            message += f"• Account Holder: {wallet.account_holder_name}\n"
        if wallet.account_number:
            message += f"• Account Number: {wallet.account_number}\n"
        if wallet.ifsc_code:
            message += f"• IFSC Code: {wallet.ifsc_code}\n"
        if wallet.bank_address:
            message += f"• Bank Address: {wallet.bank_address}\n"

    elif wallet.upload_type == 'qr':
        if wallet.qr_name:
            message += f"\n📱 QR Name: {wallet.qr_name}\n"

    elif wallet.upload_type == 'other':
        if wallet.other_name:
            message += f"\n💛 Wallet Name: {wallet.other_name}\n"

    # Add description
    if wallet.description:
        message += f"\n📝 Description:\n{wallet.description}\n"

    # Add visibility
    message += f"\n👁️ Visibility: {wallet.get_visibility_priority_display()}\n"

    # Add image link if exists
    if wallet.image:
        image_url = request.build_absolute_uri(wallet.image.url)
        message += f"\n🖼️ Image: {image_url}\n"

    # URL encode and return
    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"

    return JsonResponse({
        'whatsapp_url': whatsapp_url,
        'message': message
    })
# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Wallet
from urllib.parse import quote
import os
from django.db.models import Q

def is_admin_user(request):
    """
    Determine whether the current request should be treated as admin/superadmin.
    Checks:
      - Django superuser flag (request.user.is_superuser)
      - a session variable 'user_level' (your app stores this at login)
    Adapt the admin_levels list if your app uses different strings.
    """
    try:
        if request.user and getattr(request.user, 'is_superuser', False):
            return True
    except Exception:
        pass

    user_level = request.session.get('user_level', '')
    admin_levels = ['admin_level', '5level', '4level', 'superadmin', 'admin']
    return str(user_level) in admin_levels


def wallet_list(request):
    """Display wallets with role-based filtering.

    - Admins / superusers see ALL wallets.
    - Normal users see wallets where:
        * visibility_priority == 'user'
        OR
        * they are the creator (created_by matches request.user or session custom_user_id)
    """
    if is_admin_user(request):
        wallets = Wallet.objects.all().order_by('-created_at')
    else:
        # Owner filter: prefer Django user; fallback to custom session id 'custom_user_id' if present
        owner_q = Q()
        if request.user and request.user.is_authenticated:
            owner_q = Q(created_by=request.user)

        custom_user_id = request.session.get('custom_user_id')
        if custom_user_id:
            # include created_by id match as fallback
            owner_q = owner_q | Q(created_by__id=custom_user_id)

        user_visibility_q = Q(visibility_priority='user')

        wallets = Wallet.objects.filter(user_visibility_q | owner_q).order_by('-created_at')

    # Recompute type-specific lists from filtered wallets (so counts/sections reflect visibility)
    bank_wallets = wallets.filter(upload_type='bank')
    qr_wallets = wallets.filter(upload_type='qr')
    document_wallets = wallets.filter(upload_type='document')
    other_wallets = wallets.filter(upload_type='other')

    context = {
        'wallets': wallets,
        'bank_wallets': bank_wallets,
        'qr_wallets': qr_wallets,
        'document_wallets': document_wallets,
        'other_wallets': other_wallets,
    }

    return render(request, 'wallet_list.html', context)


def add_wallet(request):
    """Add new wallet item"""
    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        # Get the appropriate image field based on upload type
        image = None
        if upload_type == 'bank':
            image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            image = request.FILES.get('image_document')
        elif upload_type == 'other':
            image = request.FILES.get('image_other')

        # Basic validation
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

        # Handle type-specific fields
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
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
    """Edit existing wallet with permission guard (admin OR owner)."""
    wallet = get_object_or_404(Wallet, id=wallet_id)

    # Permission check: allow if admin OR owner
    allowed = False
    if is_admin_user(request):
        allowed = True
    else:
        # Owner via Django user
        if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
            allowed = True
        # Owner via custom session id
        custom_user_id = request.session.get('custom_user_id')
        if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
            try:
                if int(custom_user_id) == int(wallet.created_by.id):
                    allowed = True
            except Exception:
                pass

    if not allowed:
        messages.error(request, 'You do not have permission to edit this wallet.')
        return redirect('wallet_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'edit_wallet.html', {'wallet': wallet})

        # Get new image based on upload type
        new_image = None
        if upload_type == 'bank':
            new_image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            new_image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            new_image = request.FILES.get('image_document')
        elif upload_type == 'other':
            new_image = request.FILES.get('image_other')

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

        # Update type-specific fields
        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
            wallet.bank_address = request.POST.get('bank_address', '')
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.other_name = ''
        elif upload_type == 'document':
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''

        # Replace image if new image uploaded
        if new_image:
            try:
                if wallet.image and hasattr(wallet.image, 'path'):
                    old_path = wallet.image.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception:
                pass
            wallet.image = new_image

        wallet.save()
        messages.success(request, 'Wallet item updated successfully!')
        return redirect('wallet_list')

    return render(request, 'edit_wallet.html', {'wallet': wallet})


def delete_wallet(request, wallet_id):
    """Delete wallet item with permission guard (admin OR owner)."""
    # Only proceed if POST; otherwise redirect back
    if request.method == 'POST':
        try:
            wallet = Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet item not found.')
            return redirect('wallet_list')

        # Permission check
        allowed = False
        if is_admin_user(request):
            allowed = True
        else:
            if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
                allowed = True
            custom_user_id = request.session.get('custom_user_id')
            if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
                try:
                    if int(custom_user_id) == int(wallet.created_by.id):
                        allowed = True
                except Exception:
                    pass

        if not allowed:
            messages.error(request, 'You do not have permission to delete this wallet.')
            return redirect('wallet_list')

        # Delete image file if exists
        try:
            if wallet.image and hasattr(wallet.image, 'path'):
                if os.path.exists(wallet.image.path):
                    os.remove(wallet.image.path)
        except Exception:
            pass

        wallet.delete()
        messages.success(request, 'Wallet item deleted successfully!')

    return redirect('wallet_list')


def wallet_whatsapp_share(request, wallet_id):
    """Generate WhatsApp share link with complete wallet details"""
    wallet = get_object_or_404(Wallet, id=wallet_id)

    # Build detailed message
    message = f"*{wallet.title}*\n\n"
    message += f"📋 Type: {wallet.get_upload_type_display()}\n"

    # Add type-specific details
    if wallet.upload_type == 'bank':
        message += "\n💳 *Bank Details:*\n"
        if wallet.account_holder_name:
            message += f"• Account Holder: {wallet.account_holder_name}\n"
        if wallet.account_number:
            message += f"• Account Number: {wallet.account_number}\n"
        if wallet.ifsc_code:
            message += f"• IFSC Code: {wallet.ifsc_code}\n"
        if wallet.bank_address:
            message += f"• Bank Address: {wallet.bank_address}\n"

    elif wallet.upload_type == 'qr':
        if wallet.qr_name:
            message += f"\n📱 QR Name: {wallet.qr_name}\n"

    elif wallet.upload_type == 'other':
        if wallet.other_name:
            message += f"\n💛 Wallet Name: {wallet.other_name}\n"

    # Add description
    if wallet.description:
        message += f"\n📝 Description:\n{wallet.description}\n"

    # Add visibility
    message += f"\n👁️ Visibility: {wallet.get_visibility_priority_display()}\n"

    # Add image link if exists
    if wallet.image:
        image_url = request.build_absolute_uri(wallet.image.url)
        message += f"\n🖼️ Image: {image_url}\n"

    # URL encode and return
    encoded_message = quote(message)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"

    return JsonResponse({
        'whatsapp_url': whatsapp_url,
        'message': message
    })
