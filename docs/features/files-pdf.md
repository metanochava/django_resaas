# Ficheiros e PDF

## Ficheiros

O framework pode representar `FileField` e `ImageField` com informação
útil, como URL, nome, extensão, tamanho e tipo MIME.

## Upload

Os caminhos devem evitar colisões de nomes e respeitar a organização por
entidade/aplicação quando definida.

## PDF

A camada de utilitários pode incluir:

-   geração de PDF;
-   QR Code;
-   barcode;
-   conversão de PNG para Base64;
-   templates de documentos.

As aplicações devem concentrar a apresentação específica nos seus
templates e reutilizar os utilitários comuns.
