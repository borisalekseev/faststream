## AsyncAPI Schema

Also, the **FastStream CLI** allows you to work with the **AsyncAPI** schema in a simple way.

You are able to generate `.json` or `.yaml` files by your application code or host **HTML** representation directly:

```shell
faststream docs --help
```

```{ .console .no-copy }
Usage: faststream docs [OPTIONS] COMMAND [ARGS]...

  AsyncAPI schema commands

Options:
  --help  Show this message and exit.

Commands:
  gen    Generate project AsyncAPI schema
  serve  Serve project AsyncAPI schema
```
{ data-search-exclude }

To serve the documentation, create a simple app in the `main.py` file:

{! includes/en/simple-apps.md !}

Then run the following command:

```shell
faststream docs serve main:app
```

To learn more about the commands above, please visit [**AsyncAPI export**](../asyncapi/export.md){.internal-link} and [**AsyncAPI hosting**](../asyncapi/hosting.md){.internal-link}.
