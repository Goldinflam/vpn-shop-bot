"""Translation catalog for the bot.

Keys use dot-notation grouped by feature area. Values are ``str.format``
templates — so placeholders like ``{plan_name}`` are substituted at call
time by :meth:`bot.i18n.Translator.get`.
"""

from __future__ import annotations

from typing import Final

from shared.enums import Locale

_RU: Final[dict[str, str]] = {
    # common
    "common.back": "⬅️ Назад",
    "common.cancel": "Отмена",
    "common.error": "Что-то пошло не так, попробуйте позже.",
    "common.not_available": "Сервис временно недоступен. Попробуйте чуть позже.",
    # start / main menu
    "start.greeting": (
        "Привет, {name}! 👋\nЭто бот для покупки VPN-подписок.\n"
        "Выберите действие в меню ниже."
    ),
    "menu.trial": "🚀 Попробовать бесплатно",
    "menu.buy": "💰 Тарифы",
    "menu.my_subs": "📦 Мои подписки",
    "menu.promo": "🎁 Ввести промокод",
    "menu.help": "❓ Помощь",
    "menu.language": "🌐 Язык",
    # trial / promo / happ
    "trial.intro": "Активирую бесплатный пробный доступ…",
    "trial.already_claimed": (
        "Вы уже использовали бесплатный триал. Посмотрите тарифы в меню 💰."
    ),
    "trial.failed": "Не удалось выдать триал. Попробуйте позже.",
    "promo.prompt": (
        "Отправьте промокод одним сообщением. Для выхода — /cancel."
    ),
    "promo.applied_discount": (
        "Промокод принят! Скидка {percent}% применится к следующей оплате."
    ),
    "promo.applied_trial": "Промокод принят, выдаю VPN…",
    "promo.not_found": "Такой промокод не найден или больше недоступен.",
    "promo.expired": "Срок действия промокода истёк.",
    "promo.exhausted": "Лимит использований промокода исчерпан.",
    "promo.already_used": "Этот промокод уже применён.",
    "promo.trial_claimed": "Бесплатный триал уже использован.",
    "promo.error": "Не удалось применить промокод. Попробуйте позже.",
    "promo.cancelled": "Ввод промокода отменён.",
    "vpn.issued_header": (
        "✅ VPN готов!\n\n"
        "Нажмите «🚀 Подключиться» — Happ сам импортирует подписку."
    ),
    "vpn.happ_connect": "🚀 Подключиться",
    "vpn.open_subscription": "🔄 Открыть подписку",
    "vpn.download_happ": "📥 Скачать Happ",
    "vpn.vless_fallback": "Ручная ссылка (если кнопки не работают):\n<code>{link}</code>",
    "vpn.qr_caption": "QR-код для импорта",
    # buy flow
    "buy.pick_plan": "Выберите тариф:",
    "buy.no_plans": "Сейчас нет доступных тарифов. Загляните позже.",
    "buy.plan_card": (
        "<b>{name}</b>\n"
        "Срок: {duration_days} дн.\n"
        "Трафик: {traffic}\n"
        "Цена: {price} {currency}"
    ),
    "buy.traffic_unlimited": "безлимит",
    "buy.traffic_gb": "{gb} ГБ",
    "buy.pick_provider": "Выберите способ оплаты:",
    "buy.provider.yookassa": "💳 YooKassa",
    "buy.provider.cryptobot": "🪙 CryptoBot",
    "buy.provider.stars": "⭐ Telegram Stars",
    "buy.invoice_ready": "Счёт создан. Оплатите по ссылке ниже:",
    "buy.pay_button": "💳 Оплатить",
    "buy.check_button": "🔄 Проверить оплату",
    "buy.status_pending": "Оплата ещё не подтверждена.",
    "buy.status_succeeded": "Оплата получена! Подписка активна.",
    "buy.status_failed": "Оплата не прошла. Попробуйте ещё раз.",
    # my subs
    "subs.empty": "У вас пока нет активных подписок.",
    "subs.list_header": "Ваши подписки:",
    "subs.item": "#{id} — до {expires} ({status})",
    "subs.show_link": "🔗 Показать ссылку",
    "subs.instructions": "📖 Инструкция",
    "subs.renew": "♻️ Продлить",
    "subs.link_message": "Ваша VLESS-ссылка:\n<code>{link}</code>",
    # help
    "help.pick_os": "Выберите вашу операционную систему:",
    "help.os.android": "🤖 Android",
    "help.os.ios": "🍏 iOS",
    "help.os.windows": "🪟 Windows",
    "help.os.macos": "🍎 macOS",
    # language
    "language.pick": "Выберите язык интерфейса:",
    "language.saved": "Язык сохранён.",
    # admin
    "admin.not_allowed": "Команда доступна только администраторам.",
    "admin.stats_header": "📊 Статистика:",
    "admin.broadcast.prompt": "Отправьте текст для рассылки или /cancel.",
    "admin.broadcast.done": "Рассылка запущена. Получателей: {count}",
    "admin.broadcast.cancelled": "Рассылка отменена.",
}

_EN: Final[dict[str, str]] = {
    "common.back": "⬅️ Back",
    "common.cancel": "Cancel",
    "common.error": "Something went wrong, please try again later.",
    "common.not_available": "Service is temporarily unavailable. Try again later.",
    "start.greeting": (
        "Hi, {name}! 👋\nThis bot sells VPN subscriptions.\n"
        "Pick an action from the menu below."
    ),
    "menu.trial": "🚀 Try for free",
    "menu.buy": "💰 Plans",
    "menu.my_subs": "📦 My subscriptions",
    "menu.promo": "🎁 Enter promo code",
    "menu.help": "❓ Help",
    "menu.language": "🌐 Language",
    "trial.intro": "Activating your free trial…",
    "trial.already_claimed": (
        "You've already used your free trial. Check 💰 Plans in the menu."
    ),
    "trial.failed": "Failed to issue trial. Try again later.",
    "promo.prompt": "Send your promo code as a single message. /cancel to abort.",
    "promo.applied_discount": (
        "Promo applied! {percent}% discount will be used on your next payment."
    ),
    "promo.applied_trial": "Promo accepted, issuing VPN…",
    "promo.not_found": "Promo code not found or no longer available.",
    "promo.expired": "The promo code has expired.",
    "promo.exhausted": "Promo code usage limit reached.",
    "promo.already_used": "This promo has already been redeemed.",
    "promo.trial_claimed": "Free trial has already been used.",
    "promo.error": "Failed to apply promo code. Try again later.",
    "promo.cancelled": "Promo entry cancelled.",
    "vpn.issued_header": (
        "✅ VPN is ready!\n\n"
        "Tap \"🚀 Connect\" — Happ will import the subscription automatically."
    ),
    "vpn.happ_connect": "🚀 Connect",
    "vpn.open_subscription": "🔄 Open subscription",
    "vpn.download_happ": "📥 Download Happ",
    "vpn.vless_fallback": "Manual link (if buttons don't work):\n<code>{link}</code>",
    "vpn.qr_caption": "QR code to import",
    "buy.pick_plan": "Pick a plan:",
    "buy.no_plans": "No plans available right now. Please check back later.",
    "buy.plan_card": (
        "<b>{name}</b>\n"
        "Duration: {duration_days} days\n"
        "Traffic: {traffic}\n"
        "Price: {price} {currency}"
    ),
    "buy.traffic_unlimited": "unlimited",
    "buy.traffic_gb": "{gb} GB",
    "buy.pick_provider": "Choose a payment method:",
    "buy.provider.yookassa": "💳 YooKassa",
    "buy.provider.cryptobot": "🪙 CryptoBot",
    "buy.provider.stars": "⭐ Telegram Stars",
    "buy.invoice_ready": "Invoice created. Pay using the link below:",
    "buy.pay_button": "💳 Pay",
    "buy.check_button": "🔄 Check payment",
    "buy.status_pending": "Payment is not confirmed yet.",
    "buy.status_succeeded": "Payment received! Subscription is active.",
    "buy.status_failed": "Payment failed. Please try again.",
    "subs.empty": "You don't have any active subscriptions yet.",
    "subs.list_header": "Your subscriptions:",
    "subs.item": "#{id} — until {expires} ({status})",
    "subs.show_link": "🔗 Show link",
    "subs.instructions": "📖 Instructions",
    "subs.renew": "♻️ Renew",
    "subs.link_message": "Your VLESS link:\n<code>{link}</code>",
    "help.pick_os": "Pick your operating system:",
    "help.os.android": "🤖 Android",
    "help.os.ios": "🍏 iOS",
    "help.os.windows": "🪟 Windows",
    "help.os.macos": "🍎 macOS",
    "language.pick": "Pick an interface language:",
    "language.saved": "Language saved.",
    "admin.not_allowed": "This command is for admins only.",
    "admin.stats_header": "📊 Stats:",
    "admin.broadcast.prompt": "Send broadcast text or /cancel.",
    "admin.broadcast.done": "Broadcast started. Recipients: {count}",
    "admin.broadcast.cancelled": "Broadcast cancelled.",
}


CATALOG: Final[dict[Locale, dict[str, str]]] = {
    Locale.RU: _RU,
    Locale.EN: _EN,
}
