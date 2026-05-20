raw = open('app5/views.py', 'rb').read()

needle = b"_admin_levels = ['normal', 'admin_level', '4level']\r\n    _active_leads_qs = Lead.objects.filter(\r\n        status__in=['Active', 'New', 'Follow-up Required', 'Not Attended', 'Proposal Sent', 'On Hold']\r\n    ).select_related('created_by__branch').prefetch_related('requirements').order_by('-created_at')\r\n    if user_level not in _admin_levels and current_user_branch_id:\r\n        _active_leads_qs = _active_leads_qs.filter(requirement=current_user_branch_id)\r\n    active_leads = _active_leads_qs"

original = b"active_leads = Lead.objects.filter(\r\n        status__in=['Active', 'New', 'Follow-up Required', 'Not Attended', 'Proposal Sent', 'On Hold']\r\n    ).select_related('created_by__branch').prefetch_related('requirements').order_by('-created_at')"

count = raw.count(needle)
print('occurrences found:', count)

if count == 2:
    new_raw = raw.replace(needle, original)
    open('app5/views.py', 'wb').write(new_raw)
    print('Done - reverted both occurrences')
else:
    print('ERROR: expected 2, got', count)
