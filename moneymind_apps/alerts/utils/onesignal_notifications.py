import requests
from datetime import timedelta, datetime
import logging
from dateutil.relativedelta import relativedelta

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

    now = datetime.now()
    current_date = now.date()

    # Calcular la próxima fecha de pago
    try:
        # Intentar con el mes actual
        payment_date = reminder.start_date.replace(day=reminder.payment_day)
    except ValueError:
        # Si el día no existe en el mes (ej: 31 en febrero)
        payment_date = reminder.start_date.replace(day=1) + relativedelta(months=1, days=-1)

    # Si la fecha ya pasó este mes, usar el próximo mes
    if payment_date <= current_date:
        payment_date = payment_date + relativedelta(months=1)
        logger.info(f"📅 Fecha de pago ajustada al próximo mes: {payment_date.strftime('%d/%m/%Y')}")

    # Programar notificaciones: 3 días antes, 2 días antes, el mismo día
    notifications_scheduled = 0

    for days_before in [3, 2, 0]:
        notification_date = payment_date - timedelta(days=days_before)

        # ⭐ VERIFICAR que la fecha sea futura
        if notification_date <= current_date:
            logger.warning(
                f"⏭️ Saltando notificación para {notification_date.strftime('%d/%m/%Y')} "
                f"({days_before} días antes) - fecha en el pasado"
            )
            continue

        # Programar a las 9:00 AM hora local
        send_datetime = datetime.combine(notification_date, datetime.min.time().replace(hour=9, minute=0))

        # Convertir a UTC (OneSignal requiere UTC)
        # Perú está en UTC-5, así que sumamos 5 horas
        send_datetime_utc = send_datetime + timedelta(hours=5)
        send_after = send_datetime_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

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
                "external_id": [str(user.id)]
            },
            "target_channel": "push",
            "headings": {"en": f"💰 {urgency_text} Recordatorio de pago"},
            "contents": {
                "en": f"Tu pago '{reminder.name}' de S/ {reminder.amount} vence el {payment_date.strftime('%d/%m/%Y')}."
            },
            "send_after": send_after,
        }

        try:
            response = requests.post(base_url, headers=headers, json=payload, timeout=10)
            response_data = response.json()

            if response.status_code == 200:
                if "errors" in response_data and response_data["errors"]:
                    logger.error(
                        f"❌ Error OneSignal para user {user.id}: {response_data['errors']}"
                    )
                else:
                    notification_id = response_data.get('id', 'N/A')
                    logger.info(
                        f"✅ Notificación #{notifications_scheduled + 1} programada: "
                        f"{notification_date.strftime('%d/%m/%Y')} a las 9:00 AM "
                        f"({days_before} días antes del pago) - ID: {notification_id}"
                    )
                    notifications_scheduled += 1
            else:
                logger.error(
                    f"❌ Error OneSignal ({response.status_code}): {response_data}"
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de red con OneSignal: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error inesperado en OneSignal: {str(e)}")

    if notifications_scheduled > 0:
        logger.info(
            f"🎉 Total: {notifications_scheduled} notificaciones programadas para '{reminder.name}' "
            f"(pago el {payment_date.strftime('%d/%m/%Y')})"
        )
    else:
        logger.warning(
            f"⚠️ No se programaron notificaciones para '{reminder.name}' - "
            f"todas las fechas están en el pasado"
        )
