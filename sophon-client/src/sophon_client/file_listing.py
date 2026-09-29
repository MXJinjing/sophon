"""Typed, aligned ls-style manifest listings with optional terminal colors."""
from .progress import size


def rows(entries, current_path="."):
    for item in entries:
        kind='directory' if item.get('type')=='directory' else 'file'
        path=item['filename']
        prefix=current_path.strip('/')
        if prefix and prefix != '.':
            if path == prefix: path=item.get('name') or path.rsplit('/',1)[-1]
            elif path.startswith(prefix+'/'): path=path[len(prefix)+1:]
        amount='-' if kind=='directory' else (size(item['size']) if item.get('size') is not None else '?')
        yield kind,amount,path


def print_listing(entries,console=None,current_path="."):
    values=list(rows(entries,current_path))
    if not values:return
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        print(f"{'TYPE':10}  {'SIZE':>12}  PATH")
        for kind,amount,path in values:print(f'{kind:10}  {amount:>12}  {path}')
        return
    console=console or Console()
    table=Table(box=None,pad_edge=False,padding=(0,2),show_edge=False)
    table.add_column('TYPE',no_wrap=True)
    table.add_column('SIZE',justify='right',no_wrap=True)
    table.add_column('PATH',overflow='fold')
    for kind,amount,path in values:
        style='bold blue' if kind=='directory' else 'green'
        # Literal Text prevents bracketed file names from being interpreted as markup.
        table.add_row(Text(kind,style=style),Text(amount,style='dim'),Text(path,style=style))
    console.print(table)
