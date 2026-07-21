import os
import requests
from datetime import date, datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

BADGE_COLORES = {
    "Fotovoltaico":  ("background:#fef9c3;color:#854d0e", "☀️"),
    "Eólico":        ("background:#dbeafe;color:#1d4ed8", "💨"),
    "BESS":          ("background:#dcfce7;color:#166534", "🔋"),
    "Hibridación":   ("background:#f3e8ff;color:#7e22ce", "⚡"),
    "LAT":           ("background:#fee2e2;color:#991b1b", "🔌"),
    "SET":           ("background:#ffedd5;color:#9a3412", "🏭"),
    "Termosolar":    ("background:#fef3c7;color:#92400e", "🌡️"),
    "Hidráulica":    ("background:#e0f2fe;color:#075985", "💧"),
}


def obtener_proyectos_hoy():
    hoy = date.today().isoformat()
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/proyectos",
        headers=SUPABASE_HEADERS,
        params={
            "select": "nombre_proyecto,empresa_promotora,tecnologia,potencia_mw,tipo_tramite,provincias,comunidades_autonomas,estado_administrativo,resumen,enlace,fecha_publicacion,fuente",
            "created_at": f"gte.{hoy}T00:00:00",
            "order": "comunidades_autonomas.asc"
        }
    )
    return r.json() if r.status_code == 200 else []


def obtener_suscriptores():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/suscriptores",
        headers=SUPABASE_HEADERS,
        params={"select": "email", "activo": "eq.true"}
    )
    return [s["email"] for s in r.json()] if r.status_code == 200 else []


def badge_tecnologia(tech):
    estilo, emoji = BADGE_COLORES.get(tech, ("background:#f1f5f9;color:#475569", "⚙️"))
    return f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;{estilo}">{emoji} {tech}</span>'


def generar_html(proyectos, fecha):
    total_mw = sum(float(p.get("potencia_mw") or 0) for p in proyectos)
    ccaas = set()
    for p in proyectos:
        ccaa = p.get("comunidades_autonomas")
        if isinstance(ccaa, list):
            ccaas.update(ccaa)
        elif ccaa:
            ccaas.add(ccaa)

    resumen_dia = f"{len(proyectos)} nuevos trámites · {total_mw:,.0f} MW · {len(ccaas)} comunidades"

    # Agrupar por CCAA
    grupos = {}
    for p in proyectos:
        ccaa = p.get("comunidades_autonomas")
        if isinstance(ccaa, list):
            key = ccaa[0] if ccaa else "Sin comunidad"
        else:
            key = ccaa or "Sin comunidad"
        grupos.setdefault(key, []).append(p)

    filas_html = ""
    for ccaa, items in sorted(grupos.items()):
        filas_html += f"""
        <tr>
          <td colspan="2" style="padding:16px 0 8px 0;font-size:13px;font-weight:700;
              color:#0f172a;border-bottom:2px solid #22c55e;text-transform:uppercase;
              letter-spacing:0.05em">{ccaa}</td>
        </tr>"""
        for p in items:
            nombre = p.get("nombre_proyecto") or "—"
            empresa = p.get("empresa_promotora") or "—"
            mw = f"{p['potencia_mw']} MW" if p.get("potencia_mw") else "—"
            tramite = p.get("tipo_tramite") or "—"
            estado = p.get("estado_administrativo") or "—"
            resumen = p.get("resumen") or ""
            enlace = p.get("enlace") or "#"
            fuente = p.get("fuente") or ""
            tech = p.get("tecnologia") or "OTRO"

            filas_html += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f1f5f9;vertical-align:top">
            <div style="font-weight:600;font-size:14px;color:#0f172a;margin-bottom:4px">{nombre}</div>
            <div style="font-size:12px;color:#64748b;margin-bottom:6px">{empresa}</div>
            <div style="margin-bottom:6px">{badge_tecnologia(tech)}</div>
            <div style="font-size:12px;color:#64748b">{resumen[:180]}{"..." if len(resumen) > 180 else ""}</div>
          </td>
          <td style="padding:12px 0 12px 16px;border-bottom:1px solid #f1f5f9;
              vertical-align:top;white-space:nowrap;text-align:right">
            <div style="font-weight:700;font-size:16px;color:#0f172a">{mw}</div>
            <div style="font-size:11px;color:#64748b;margin-top:2px">{tramite}</div>
            <div style="font-size:11px;color:#64748b">{estado}</div>
            <div style="margin-top:8px">
              <a href="{enlace}" style="font-size:11px;color:#22c55e;text-decoration:none;
                  font-weight:600">{fuente} ↗</a>
            </div>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 16px">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%">

        <!-- CABECERA -->
        <tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:28px 32px">
          <div style="font-size:22px;font-weight:700;color:white">⚡ TramitaRenova</div>
          <div style="font-size:13px;color:#94a3b8;margin-top:4px">
            Inteligencia regulatoria renovable · {fecha}
          </div>
          <div style="margin-top:16px;background:#1e293b;border-radius:8px;
              padding:12px 16px;font-size:14px;color:#22c55e;font-weight:600">
            {resumen_dia}
          </div>
        </td></tr>

        <!-- CONTENIDO -->
        <tr><td style="background:white;padding:24px 32px">
          <table width="100%" cellpadding="0" cellspacing="0">
            {filas_html}
          </table>
        </td></tr>

        <!-- PIE -->
        <tr><td style="background:#f8fafc;border-radius:0 0 12px 12px;
            padding:20px 32px;text-align:center;border-top:1px solid #e2e8f0">
          <div style="font-size:12px;color:#94a3b8">
            Datos extraídos automáticamente de boletines oficiales españoles ·
            Actualización diaria
          </div>
          <div style="margin-top:8px;font-size:12px">
            <a href="https://tramitarenova.lovable.app"
               style="color:#22c55e;text-decoration:none">Ver web completa</a>
            &nbsp;·&nbsp;
            <a href="https://tramitarenova.lovable.app/unsubscribe"
               style="color:#94a3b8;text-decoration:none">Darse de baja</a>
          </div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return html


def enviar_newsletter(destinatarios=None, proyectos=None):
    if proyectos is None:
        proyectos = obtener_proyectos_hoy()

    if not proyectos:
        print("📭 Sin proyectos nuevos hoy — no se envía newsletter")
        return False

    if destinatarios is None:
        destinatarios = obtener_suscriptores()

    if not destinatarios:
        print("📭 Sin suscriptores activos")
        return False

    MESES_ES = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    hoy = date.today()
    fecha_str = f"{hoy.day} de {MESES_ES[hoy.month]} de {hoy.year}"
    html = generar_html(proyectos, fecha_str)
    total_mw = sum(float(p.get("potencia_mw") or 0) for p in proyectos)
    asunto = f"⚡ TramitaRenova · {len(proyectos)} trámites renovables · {total_mw:,.0f} MW · {date.today().strftime('%d/%m/%Y')}"

    enviados = 0
    for email in destinatarios:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": "TramitaRenova <onboarding@resend.dev>",
                "to": [email],
                "subject": asunto,
                "html": html
            }
        )
        if r.status_code in [200, 201]:
            print(f"✅ Email enviado a {email}")
            enviados += 1
        else:
            print(f"⚠️ Error enviando a {email}: {r.status_code} {r.text[:100]}")

    print(f"📧 Newsletter enviada: {enviados}/{len(destinatarios)} destinatarios")
    return enviados > 0


if __name__ == "__main__":
    # Prueba directa: envía solo a danimacotera@gmail.com con proyectos de hoy
    enviar_newsletter(destinatarios=["danimacotera@gmail.com"])
