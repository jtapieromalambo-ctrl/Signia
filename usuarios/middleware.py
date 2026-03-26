from django.shortcuts import redirect

class AdminLoginRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated:
                return redirect('/login/')
            if not request.user.is_superuser:
                return redirect('/login/')
        
        response = self.get_response(request)
        return response