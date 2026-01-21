from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = 'pages/about.html'


class FAQView(TemplateView):
    template_name = 'pages/faq.html'


class ErrorView(TemplateView):
    template_name = 'pages/error.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = self.request.GET.get('message', 'An unexpected error occurred.')
        return context