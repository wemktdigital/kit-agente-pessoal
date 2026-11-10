"""Gera assets/emoji/*.png (160 px) a partir da Apple Color Emoji. Só roda no Mac.

Uso: python gerar_emoji.py [emoji ...]   (sem argumentos, gera a lista abaixo)
Precisa de Pillow (ex.: ~/tools/Applio/.venv/bin/python).
"""
import sys

from PIL import Image, ImageDraw, ImageFont

from emoji_img import PNG_DIR, nome

FONTE = "/System/Library/Fonts/Apple Color Emoji.ttc"

LISTA = """
⭐ 👇 ❌ 👉 🤔 ✅ 🏆 😍 💚 👀 ✋ 🤖 🚫 😅 🫠 🚀 🎯 🔗 🙅 🗣️ 👏 📷 💬 🔎 👍 🧐 🚨 🙋 🤷 🤹 💼 🔀 😬 🔑 💡 📆 📝 👤
❤️ 👥 🤝 💸 😤 🛡️ 😐 😡 ⚙️ 📲 📈 📊 📍 🙏 😊 🙌 🎁 🙅‍♂️ 😶 🤫 📱 🗺️ 😎 🙈 📦 🌱 ⚠️
😀 😃 😄 😁 😆 🤣 😂 🙂 🙃 😉 😇 🥰 😘 😋 😛 😜 🤪 😝 🤑 🤗 🤭 🫢 🫣 🤐 🤨 😑 😏 😒 🙄 😮‍💨 🤥 😌 😔 😪 🤤 😴
😷 🤒 🤕 🤢 🤮 🥵 🥶 🥴 😵 😵‍💫 🤯 🤠 🥳 🥸 😕 🫤 😟 🙁 ☹️ 😮 😯 😲 😳 🥺 🥹 😦 😧 😨 😰 😥 😢 😭 😱 😖 😣 😞
😓 😩 😫 🥱 😠 🤬 😈 💀 🤡 👻 🫡 🥲 😶‍🌫️ 🫥
👋 🤚 🖐️ 🖖 👌 🤌 🤏 ✌️ 🤞 🫰 🤟 🤘 🤙 👈 👆 ☝️ 🫵 👎 ✊ 👊 🤛 🤜 🫶 👐 🤲 ✍️ 💪 🧠 🫀 🦷 👁️
🧑 👨 👩 🧑‍⚕️ 👨‍⚕️ 👩‍⚕️ 🙋‍♂️ 🙋‍♀️ 🤷‍♂️ 🤷‍♀️ 🙅‍♀️ 🙆 🤦 🤦‍♂️ 🤦‍♀️ 💁 🧏 🏃 🧘 💃 🕺
🧡 💛 💙 💜 🖤 🤍 💔 ❣️ 💕
☑️ ✔️ ❎ ⭕ ❗ ❓ ❕ ❔ ‼️ ⁉️ 💯 🔥 ✨ 🌟 💫 ⚡ 🎉 🎊 🥇 🥈 🥉 📉 📌 🔒 🔓 🔔 🔕 📣 📢 💭
🩺 💊 💉 🩹 🩻 🏥 🚑 ⏰ ⏳ ⌛ 📅 🗓️ 📋 📄 📃 🧾 📁 📂 💰 💵 💳 🏦 🛒 💻 🖥️ ⌨️ 🖱️ 📸 🎥 🎬 📞 ☎️
📧 ✉️ 📩 🔍 🛠️ 🔧 🧰 🌍 🌎 🏠 🏢 🧲 🪄 🎨 ✏️ 🖊️ 📚 📖 🔁 🔄 ➡️ ⬅️ ⬆️ ⬇️ ↗️ ↘️ 🔝 🆕 🆓 🆗
🟢 🟡 🔴 🔵 ⚪ ⚫ 🟩 🟥 🟨 🟦 ⬛ ⬜ 🔶 🔷 ▶️ ⏸️ 🌿 🍀 ☕ 🍎 🙉 🙊 🦄 🎤 🎧 🎵 🎶
""".split()


def gera(e, fonte):
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), e, font=fonte, embedded_color=True)
    if not im.getbbox():
        return False
    im.save(PNG_DIR / f"{nome(e)}.png", optimize=True)
    return True


if __name__ == "__main__":
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    fonte = ImageFont.truetype(FONTE, 160)
    falhou = [e for e in dict.fromkeys(sys.argv[1:] or LISTA) if not gera(e, fonte)]
    print(len(list(PNG_DIR.glob("*.png"))), "PNG em", PNG_DIR)
    if falhou:
        print("não renderizou:", " ".join(falhou))
