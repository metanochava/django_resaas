class UserName:
    """
    Gerador de usernames únicos.
    """

    @staticmethod
    def Create(name):
        from django.apps import apps  # lazy import

        User = apps.get_model('django_saas', 'User')

        try:
            user = User.objects.get(username=name)
        except User.DoesNotExist:
            return name

        username = user.username

        # separar letras e números
        letras = "".join(filter(str.isalpha, username))
        numeros = "".join(filter(str.isdigit, username))

        numero = int(numeros) if numeros else 0
        novo_username = f"{letras}{numero + 1}"

        return UserName.Create(novo_username)
