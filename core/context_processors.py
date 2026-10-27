from core.models import SiteConfig


def site_config(request):
    """Pone la configuración del negocio en todas las plantillas."""
    return {"site": SiteConfig.get()}
