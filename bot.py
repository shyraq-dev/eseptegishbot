import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = Router()

def get_calculator_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="C", callback_data="clear"),
            InlineKeyboardButton(text="⌫", callback_data="backspace"),
            InlineKeyboardButton(text="( )", callback_data="brackets"),
            InlineKeyboardButton(text="%", callback_data="%"),
        ],
        [
            InlineKeyboardButton(text="7", callback_data="7"),
            InlineKeyboardButton(text="8", callback_data="8"),
            InlineKeyboardButton(text="9", callback_data="9"),
            InlineKeyboardButton(text="÷", callback_data="/"),
        ],
        [
            InlineKeyboardButton(text="4", callback_data="4"),
            InlineKeyboardButton(text="5", callback_data="5"),
            InlineKeyboardButton(text="6", callback_data="6"),
            InlineKeyboardButton(text="×", callback_data="*"),
        ],
        [
            InlineKeyboardButton(text="1", callback_data="1"),
            InlineKeyboardButton(text="2", callback_data="2"),
            InlineKeyboardButton(text="3", callback_data="3"),
            InlineKeyboardButton(text="−", callback_data="-"),
        ],
        [
            InlineKeyboardButton(text="+/−", callback_data="sign"),
            InlineKeyboardButton(text="0", callback_data="0"),
            InlineKeyboardButton(text=".", callback_data="."),
            InlineKeyboardButton(text="+", callback_data="+"),
        ],
        [
            InlineKeyboardButton(text="=", callback_data="="),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def calculate_with_percent(expression: str) -> float:
    """
    Пайызды есептеу:

    Қосу/Азайту: N ± m% = N ± (N × m/100)
    Көбейту: N × m% = N × (m/100)
    Бөлу: N ÷ m% = N ÷ (m/100)

    Мысалдар:
    20 - 12% = 20 - (20 × 12/100) = 20 - 2.4 = 17.6
    100 + 15% = 100 + (100 × 15/100) = 100 + 15 = 115
    50 × 10% = 50 × (10/100) = 50 × 0.1 = 5
    50 ÷ 10% = 50 ÷ (10/100) = 50 ÷ 0.1 = 500
    """
    expr = expression.replace('×', '*').replace('÷', '/').replace('−', '-')

    # % бар ма тексеру
    if '%' not in expr:
        return eval(expr)

    # Pattern: N оператор m%
    pattern = r'([\d.]+)\s*([+\-*/])\s*([\d.]+)%'
    match = re.search(pattern, expr)

    if match:
        base = float(match.group(1))           # N (негізгі сан)
        operator = match.group(2)              # оператор (+ - * /)
        percent_value = float(match.group(3))  # m (пайыз мәні)

        # Операторға байланысты формула
        if operator in ['+', '-']:
            # Қосу/Азайту: N ± (N × m/100)
            percent_amount = base * (percent_value / 100)

            if operator == '+':
                result = base + percent_amount
            else:  # operator == '-'
                result = base - percent_amount

        elif operator in ['*', '/']:
            # Көбейту/Бөлу: N × (m/100) немесе N ÷ (m/100)
            percent_fraction = percent_value / 100

            if operator == '*':
                result = base * percent_fraction
            else:  # operator == '/'
                if percent_fraction != 0:
                    result = base / percent_fraction
                else:
                    raise ZeroDivisionError
        else:
            result = base

        return result

    # Егер сәйкес келмесе, қарапайым есептеу
    return eval(expr)

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        text="🧮 <b>Калькулятор</b>\n\n<code>0</code>",
        reply_markup=get_calculator_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data)
async def calculator_callback(callback: CallbackQuery):
    data = callback.data
    current_text = callback.message.text

    # Өрнекті алу
    lines = current_text.split("\n\n")
    if len(lines) >= 2:
        expression = lines[-1].replace("<code>", "").replace("</code>", "").strip()
    else:
        expression = "0"

    # = бар ма тексеру
    has_result = "=" in expression

    # Егер = бар болса, нәтижені алу
    if has_result:
        parts = expression.split("=")
        last_result = parts[-1].strip()
    else:
        last_result = None

    new_expression = expression

    try:
        if data == "clear":
            new_expression = "0"

        elif data == "backspace":
            if has_result:
                new_expression = "0"
            elif len(expression) > 1:
                new_expression = expression[:-1]
            else:
                new_expression = "0"

        elif data == "brackets":
            # Жақша қосу
            open_count = expression.count("(")
            close_count = expression.count(")")

            if has_result:
                new_expression = "("
            elif open_count > close_count and (expression[-1].isdigit() or expression[-1] == ')'):
                new_expression = expression + ")"
            else:
                if expression == "0":
                    new_expression = "("
                else:
                    new_expression = expression + "("

        elif data == "sign":
            # +/- (таңба ауыстыру)
            if has_result:
                if last_result.startswith("-"):
                    new_expression = last_result[1:]
                else:
                    new_expression = f"-{last_result}"
            else:
                # Соңғы санды табу және таңбасын өзгерту
                numbers = re.findall(r'-?\d+\.?\d*', expression)
                if numbers:
                    last_num = numbers[-1]
                    idx = expression.rfind(last_num)
                    if last_num.startswith("-"):
                        new_num = last_num[1:]
                    else:
                        new_num = f"-{last_num}"
                    new_expression = expression[:idx] + new_num + expression[idx+len(last_num):]

        elif data == "=":
            if has_result:
                await callback.answer("✅ Нәтиже дайын!")
                return

            try:
                # Есептеу
                result = calculate_with_percent(expression)

                if isinstance(result, float):
                    if result.is_integer():
                        result = int(result)
                    else:
                        # Дәлдікті сақтау
                        result = round(result, 10)
                        result_str = f"{result:.10f}".rstrip('0').rstrip('.')
                        result = float(result_str) if '.' in result_str else int(float(result_str))

                new_expression = f"{expression} = {result}"

            except ZeroDivisionError:
                new_expression = "❌ 0-ге бөлуге болмайды!"
            except Exception as e:
                logger.error(f"Есептеу қатесі: {e}")
                new_expression = "❌ Қате өрнек!"

        elif data in ["+", "-", "*", "/", "%"]:
            if has_result:
                new_expression = last_result + data
            elif expression and expression[-1] in "+-*/.%":
                new_expression = expression[:-1] + data
            elif expression and expression != "0":
                new_expression = expression + data
            else:
                new_expression = expression

        elif data == ".":
            if has_result:
                new_expression = "0."
            else:
                # Соңғы санда . бар ма тексеру
                parts = re.split(r'[+\-*/%()\s]', expression)
                last_num = parts[-1] if parts else ""

                if "." not in last_num:
                    new_expression = expression + data

        else:  # Цифрлар 0-9
            if has_result:
                new_expression = data
            elif expression == "0":
                new_expression = data
            else:
                new_expression = expression + data

        # Егер өзгеріс жоқ болса
        if new_expression == expression:
            await callback.answer()
            return

        # Хабарламаны жаңарту
        await callback.message.edit_text(
            text=f"🧮 <b>Калькулятор</b>\n\n<code>{new_expression}</code>",
            reply_markup=get_calculator_keyboard(),
            parse_mode="HTML"
        )

        await callback.answer()

    except Exception as e:
        error_msg = str(e)
        if "message is not modified" not in error_msg.lower():
            logger.error(f"Callback қатесі: {e}")
            await callback.answer("⚠️ Қате орын алды!")
        else:
            await callback.answer()

async def main():
    BOT_TOKEN = "8570492218:AAFfJXdUGYf9FgAIS8MRXaKv5jbep21IUqw"

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("🚀 Бот іске қосылып жатыр...")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("=" * 50)
    print("🧮 КАЛЬКУЛЯТОР БОТ")
    print("📦 Aiogram 3.24.0")
    print("Формулалар:")
    print("  N ± m% = N ± (N × m/100)")
    print("  N × m% = N × (m/100)")
    print("  N ÷ m% = N ÷ (m/100)")
    print("=" * 50)
    asyncio.run(main())
