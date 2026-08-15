import os
import threading
from flask import Flask
from pymongo import MongoClient
import discord
from discord.ext import commands

# =========================
# ⚙️ إعدادات الرتب (البوت الثالث)
# =========================
ADMIN_ROLES = {
    1533463569683845160,
    1533463570564649121
}

# الرتب الـ 3 المسموح لها باستخدام أمر #توب
TOP_ALLOWED_ROLES = {
    1533463569683845160,
    1533463570564649121,
    1534284534210629856
}

# =========================
# 🗄️ MongoDB (قاعدة بيانات منفصلة)
# =========================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["pointsbot"]
points_collection = db["points_bot3"]  # خزانة منفصلة تماماً للبوت الثالث

# =========================
# 🤖 إعداد البوت
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="#", intents=intents, help_command=None)

# =========================
# 🔐 الدوال المساعدة
# =========================
def has_admin_permission(member):
    return any(role.id in ADMIN_ROLES for role in member.roles)

def has_top_permission(member):
    return any(role.id in TOP_ALLOWED_ROLES for role in member.roles)

def get_points(user_id):
    user = points_collection.find_one({"_id": str(user_id)})
    return user["points"] if user else 0

def set_points(user_id, points):
    points_collection.update_one(
        {"_id": str(user_id)},
        {"$set": {"points": points}},
        upsert=True
    )

# =========================
# 📡 أحداث البوت
# =========================
@bot.event
async def on_ready():
    print(f"Bot 3 Logged in as: {bot.user}")

# =========================
# 📜 الأوامر الرسمية (#)
# =========================
@bot.command(name="مساعدة")
async def help_command(ctx):
    embed = discord.Embed(
        title="📋 قائمة أوامر البوت الثالث",
        description=(
            "`#نقاط @العضو +5` ➜ إضافة نقاط\n"
            "`#نقاط @العضو -5` ➜ خصم نقاط\n"
            "`#نقاط @العضو` ➜ عرض نقاط العضو\n"
            "`#توب` ➜ أفضل 10 أعضاء (للرتب المحددة)\n"
            "`#تصفير` ➜ تصفير جميع النقاط\n"
            "`#تصفير @العضو` ➜ تصفير نقاط عضو معين"
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="نقاط")
async def points(ctx, member: discord.Member = None, amount: str = None):
    if member is None:
        member = ctx.author

    if amount is None:
        user_points = get_points(member.id)
        await ctx.send(f"⭐ نقاط {member.mention}: **{user_points}**")
        return

    if not has_admin_permission(ctx.author):
        await ctx.send("❌ ليس لديك صلاحية لإضافة أو خصم النقاط.")
        return

    try:
        val = int(amount)
    except ValueError:
        await ctx.send("❌ صيغة غير صحيحة! مثال: `#نقاط @العضو +5`")
        return

    current = max(0, get_points(member.id) + val)
    set_points(member.id, current)

    if val >= 0:
        await ctx.send(f"✅ تمت إضافة **{val}** نقطة إلى {member.mention}\n⭐ المجموع: **{current}**")
    else:
        await ctx.send(f"✅ تم خصم **{abs(val)}** نقطة من {member.mention}\n⭐ المجموع: **{current}**")

@bot.command(name="توب")
async def top(ctx):
    if not has_top_permission(ctx.author):
        await ctx.send("❌ ليس لديك صلاحية لاستخدام أمر التوب.")
        return

    users = list(points_collection.find().sort("points", -1).limit(10))
    if not users:
        await ctx.send("📭 لا توجد نقاط حتى الآن في هذا البوت.")
        return

    description = ""
    for index, user in enumerate(users, start=1):
        member = ctx.guild.get_member(int(user["_id"]))
        name = member.display_name if member else f"<@{user['_id']}>"
        medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"**{index}.**"
        description += f"{medal} {name} — ⭐ **{user['points']}**\n"

    embed = discord.Embed(title="🏆 قائمة المتصدرين", description=description, color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="تصفير", aliases=["ريست", "reset"])
async def reset_points(ctx, member: discord.Member = None):
    if not has_admin_permission(ctx.author):
        await ctx.send("❌ ليس لديك صلاحية لإجراء التصفير.")
        return

    if member:
        set_points(member.id, 0)
        await ctx.send(f"🔄 تم تصفير نقاط {member.mention} بنجاح!")
    else:
        points_collection.delete_many({})
        await ctx.send("⚠️ **تم تصفير جميع نقاط هذا البوت بنجاح!**")

# =========================
# 🌐 Flask (Keep Alive Web Server)
# =========================
app = Flask(__name__)
@app.route("/")
def home(): 
    return "Bot 3 is Running Live!"

def run_flask(): 
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.getenv("DISCORD_TOKEN"))
