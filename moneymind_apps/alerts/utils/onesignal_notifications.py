import requests
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)

ONESIGNAL_APP_ID = "64b2a598-c69a-40bc-9b73-300085bcca04"
ONESIGNAL_API_KEY = "os_v2_app_mszklgggtjalzg3tgaailpgkaq7jbsolh7ieke5p3sduqj534fxgibgoq6wn4byooqpeyhinctlb3wjuot2x7goe7prfzzdm5uvvdkq"


def schedule_recurring_payment_notifications(user, reminder):
    """
    Programa notificaciones push en OneSignal para los días antes del pago.
    """
    base_url = "https://api.onesignal.com/notifications"
    headers = {
        "Authorization": f"Basic {ONESIGNAL_API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # Calcular fechas
    payment_date = reminder.start_date.replace(day=reminder.payment_day)
    now = datetime.now().date()

    # Si la fecha ya pasó, programar para el próximo mes
    if payment_date < now:
        from dateutil.relativedelta import relativedelta
        payment_date = payment_date + relativedelta(months=1)

    # 3 días antes, 2 días antes y el mismo día
    for days_before in [3, 2, 0]:
        send_date = datetime.combine(
            payment_date - timedelta(days=days_before),
            datetime.min.time().replace(hour=9, minute=0)  # 9:00 AM
        )

        # Formato ISO 8601 UTC
        send_after = send_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Texto dinámico según días restantes
        if days_before == 3:
            urgency_text = "¡Quedan 3 días!"
        elif days_before == 2:
            urgency_text = "¡Quedan 2 días!"
        else:
            urgency_text = "¡Es hoy!"

        payload = {
            "app_id": ONESIGNAL_APP_ID,
            "include_aliases": {
                "external_id": [str(user.id)]  # ✅ Usar external_id en lugar de include_external_user_ids
            },
            "target_channel": "push",  # ✅ Especificar canal
            "headings": {"en": f"💰 {urgency_text} Recordatorio de pago"},
            "contents": {
                "en": f"Tu pago '{reminder.name}' de S/ {reminder.amount} vence el {payment_date.strftime('%d/%m/%Y')}."
            },
            "send_after": send_after,
            "delayed_option": "timezone",
            "timezone": "America/Lima",
        }

        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=10)
            response_data = response.json()

            if response.status_code == 200:
                if "errors" in response_data and response_data["errors"]:
                    logger.warning(
                        f"⚠️ OneSignal warning para user {user.id}: {response_data['errors']}"
                    )
                else:
                    logger.info(
                        f"✅ Notificación programada para {send_date.strftime('%d/%m/%Y')} "
                        f"({days_before} días antes) - ID: {response_data.get('id', 'N/A')}"
                    )
            else:
                logger.error(
                    f"❌ Error OneSignal ({response.status_code}): {response_data}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de red con OneSignal: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error inesperado en OneSignal: {str(e)}")