from datetime import date


def year(request):
    now = date.today().year
    return {'year': now}
