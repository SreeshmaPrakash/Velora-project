from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from functools import wraps

def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('userlogin')
        
        if not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('userhome')  # or wherever you want to redirect non-superusers
            
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view