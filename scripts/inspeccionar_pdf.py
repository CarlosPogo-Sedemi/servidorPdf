"""Lista los campos de un PDF editable y genera un JSON de ejemplo.

Uso (desde la raíz del proyecto):
    python -m scripts.inspeccionar_pdf templates_pdf/MI_FORMULARIO.pdf
Crea al lado del PDF: MI_FORMULARIO.campos.json  (el 'data' listo para llenar).
"""
import json
import sys
from pathlib import Path

from functions.pdf_form_service import listar_campos, payload_ejemplo


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    ruta = Path(sys.argv[1])
    campos = listar_campos(ruta.read_bytes())

    print(f"{'#':>3}  {'TIPO':<9} {'PÁG':>3}  NOMBRE (usa este nombre en el JSON)")
    for i, c in enumerate(campos, start=1):
        extra = f"  opciones={c['opciones']}" if c["opciones"] else ""
        extra += "  [multilínea]" if c["multilinea"] else ""
        print(f"{i:>3}  {c['tipo']:<9} {c['pagina']:>3}  {c['nombre']}{extra}")

    salida = ruta.with_suffix(".campos.json")
    salida.write_text(json.dumps(payload_ejemplo(campos), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(campos)} campos. JSON de ejemplo: {salida}")


if __name__ == "__main__":
    main()
