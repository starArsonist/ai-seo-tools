class SeoToolsError(RuntimeError):
    """Ошибка, текст которой можно показать пользователю как есть."""


class NotConfigured(SeoToolsError):
    """Не хватает ключа или файла для одного из источников."""
