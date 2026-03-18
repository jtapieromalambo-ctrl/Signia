def disability_modal(request):
    show_modal = False
    if request.user.is_authenticated:
        show_modal = request.session.pop('show_disability_modal', False)
    return {'show_disability_modal': show_modal}