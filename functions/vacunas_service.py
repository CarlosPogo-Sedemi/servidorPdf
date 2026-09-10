from jinja2 import Environment, FileSystemLoader
import weasyprint

env = Environment(loader=FileSystemLoader("templates_html"))


def construir_filas_vacuna(vacunas: list) -> list:
    grupos = []
    for vac in vacunas:
        doses = []

        if vac.get("FechaPrimeraDosis"):
            doses.append({
                "dosis": "1°",
                "fecha": vac.get("FechaPrimeraDosis", "").replace("-", "/"),
                "lote": vac.get("lote1", ""),
                "responsable": vac.get("Responsable1", ""),
                "establecimiento": vac.get("Establecimiento1", ""),
                "observacion": vac.get("Observacion1", ""),
            })

        for act in vac.get("ListaActividades", []):
            num_dosis = act.get("NumeroDosis", "")
            if "Dosis" in num_dosis:
                num_dosis = num_dosis.replace("Dosis ", "") + "°"

            fecha = (act.get("FechaReal") or act.get("FechaTentativa") or "").replace("-", "/")

            doses.append({
                "dosis": num_dosis,
                "fecha": fecha,
                "lote": act.get("Lote", ""),
                "responsable": act.get("ResponsableVacuna", ""),
                "establecimiento": act.get("Establecimiento", ""),
                "observacion": act.get("Observacion", ""),
            })

        if not doses:
            doses.append({"dosis": "1°", "fecha": "", "lote": "", "responsable": "", "establecimiento": "", "observacion": ""})

        grupos.append({"nombre": vac.get("NombreVacuna", ""), "dosis": doses})

    return grupos


def generar_pdf_vacunas(paciente: dict, vacunas: list) -> bytes:
    grupos = construir_filas_vacuna(vacunas)
    template = env.get_template("vacunas.html")
    html_str = template.render(paciente=paciente, grupos=grupos)
    return weasyprint.HTML(string=html_str).write_pdf()