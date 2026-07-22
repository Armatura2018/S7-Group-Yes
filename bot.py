import discord
from discord import app_commands
from discord.ext import commands
import datetime
import asyncio
import os
import json
from pathlib import Path

DATA_DIR = Path("/app/data")
if not DATA_DIR.exists():
    DATA_DIR = Path("./data")

DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = DATA_DIR / "config.json"

# --- ЦВЕТОВАЯ ПАЛИТРА БРЕНДА ---
EMBED_COLOR = discord.Color(0xbddc03) # Твой кастомный цвет #bddc03

# --- ЛОКАЛИЗАЦИЯ И ТЕКСТЫ (Официальный стиль S7 Airlines) ---
TRANSLATIONS = {
    'ru': {
        'dm_welcome_title': "Спасибо за открытие обращения",
        'dm_welcome_desc': "-# Для того чтобы наша команда могла оказать вам помощь как можно быстрее, пожалуйста, опишите ваш запрос максимально подробно. Мы оперативно передадим его дежурным агентам поддержки.",
        'ask_description': "Пожалуйста, подробно опишите суть вашего вопроса в одном сообщении ниже.",
        'footer_bot': "Вы сейчас разговариваете с ботом",
        'footer_agent': "Вы сейчас разговариваете с агентом",
        'check_dm_title': "Обращение формируется",
        'check_dm_desc': "Пожалуйста, проверьте ваши личные сообщения для продолжения диалога.",
        'check_dm_btn': "Перейти в ЛС",
        'ticket_opened_title': "Обращение открыто",
        'ticket_opened_desc': "> Ваш запрос был успешно зарегистрирован. Агенты клиентской службы уведомлены о вашем обращении. Благодарим за ожидание.",
        'eta_text': "\n\nОжидаемое время ответа агента составляет: **{eta}**.\n-# Данное время является ориентировочным. В периоды высокой загрузки службы поддержки время ожидания может быть увеличено.",
        'rejected_title': "Запрос отклонен",
        'rejected_desc': "Приносим свои извинения, но агенты поддержки посчитали ваш запрос некорректным или недостаточно информативным для открытия сессии.",
        'accepted_title': "Клиентская поддержка",
        'accepted_desc': "### Ваш запрос был принят в работу\n> Благодарим за обращение в службу поддержки S7 Airlines. Вы были успешно подключены к нашему агенту. Мы стремимся к обеспечению наивысшего уровня сервиса и надеемся предоставить вам всю необходимую помощь.",
        'accepted_instruction': "\n\n-# Чтобы мы могли оказать вам более эффективную помощь, пожалуйста, формулируйте свой запрос четко и кратко, это позволит нам предоставить точную и своевременную поддержку. Просим вас проявить терпение и вежливость, пока мы работаем над тем, чтобы помочь вам.",
        'still_here_title': "Вы еще здесь?",
        'still_here_desc': "> Поскольку мы не получили от вас ответа по решению вашего вопроса, мы просим подтвердить актуальность вашего обращения.",
        'still_here_warning': "\n\n-# Если вам требуется дополнительное время для сбора информации или у вас остались вопросы, пожалуйста, отправьте любое сообщение в этот чат. В противном случае запрос будет автоматически закрыт через 6 часов.",
        'closed_title': "Вопрос решен",
        'closed_desc': "> Благодарим за обращение в службу поддержки S7 Airlines. Мы были рады помочь вам в решении вашего вопроса. Пожалуйста, не стесняйтесь обращаться к нам снова при возникновении трудностей.",
        'closed_footer': "\n-# Мы всегда доступны для решения ваших вопросов. Спасибо за выбор S7 Airlines.",
        'closed_action_footer': "Отвечая на это сообщение, вы откроете новое обращение",
        'client_title': "Клиент",
        'staff_closed_title': "Обращение закрыто",
        'staff_closed_desc': "> Текущая сессия поддержки была успешно завершена и перемещена в архив.\n\n**Инициатор закрытия:** {reason}",
        'staff_reason_manual': "Агент поддержки",
        'staff_reason_timeout': "Тайм-аут неактивности клиента",
        'staff_closed_footer': "Архив клиентской службы S7 Airlines",
        'topic_title': "Выберите тему вашего обращения:",
        'topic_placeholder': "Выберите категорию...",
        'topics': {
            'general': {
                'label': "Общие вопросы",
                'desc': "Вопросы по игре, сервисам или общие консультации",
                'emoji': "❓"
            },
            'staff': {
                'label': "Вопросы по персоналу",
                'desc': "Жалобы, вопросы по работе администрации или штата",
                'emoji': "👥"
            },
            'partnership': {
                'label': "Партнерские вопросы",
                'desc': "Сотрудничество, медиа и коммерция",
                'emoji': "🤝"
            }
        }
    },
    'en': {
        'dm_welcome_title': "Thank you for opening a ticket",
        'dm_welcome_desc': "-# To help our team assist you as quickly as possible, please describe your request in maximum detail. We will promptly forward it to our support agents.",
        'ask_description': "Please describe the details of your issue in a single message below.",
        'footer_bot': "You are currently talking to a bot",
        'footer_agent': "You are currently talking to an agent",
        'check_dm_title': "Ticket is being created",
        'check_dm_desc': "Please check your Direct Messages to continue.",
        'check_dm_btn': "Go to DMs",
        'ticket_opened_title': "Ticket Opened",
        'ticket_opened_desc': "> Your request has been successfully registered. Support agents have been notified. Thank you for your patience.",
        'eta_text': "\n\nExpected response time: **{eta}**.\n-# This time is approximate. During peak hours, response times may be longer.",
        'rejected_title': "Request Rejected",
        'rejected_desc': "We apologize, but our support agents deemed your request incorrect or insufficient to open a support session.",
        'accepted_title': "Customer Support",
        'accepted_desc': "### Your request has been accepted\n> Thank you for contacting S7 Airlines Support. You have been successfully connected to our support agent. We strive to provide the highest level of service and hope to resolve your request efficiently.",
        'accepted_instruction': "\n\n-# To help us assist you more effectively, please keep your responses clear and concise. This allows us to provide accurate and timely support. We kindly ask for your patience and courtesy while we work to assist you.",
        'still_here_title': "Are you still here?",
        'still_here_desc': "> As we have not received a response regarding your issue, we kindly ask you to confirm if you still need assistance.",
        'still_here_warning': "\n\n-# If you need additional time or have further questions, please send a message in this chat. Otherwise, this ticket will automatically close in 6 hours.",
        'closed_title': "Issue Resolved",
        'closed_desc': "> Thank you for contacting S7 Airlines Support. It was our pleasure to assist you. Please do not hesitate to reach out to us again if you encounter any issues.",
        'closed_footer': "\n-# We are always available to resolve your issues. Thank you for choosing S7 Airlines.",
        'closed_action_footer': "Replying to this message will open a new support ticket",
        'client_title': "Client",
        'staff_closed_title': "Ticket Closed",
        'staff_closed_desc': "> The current support session has been successfully completed and archived.\n\n**Closed by:** {reason}",
        'staff_reason_manual': "Support Agent",
        'staff_reason_timeout': "Client Inactivity Timeout",
        'staff_closed_footer': "S7 Airlines Customer Service Archive",
        'topic_title': "Select the topic of your request:",
        'topic_placeholder': "Select a category...",
        'topics': {
            'general': {
                'label': "General Questions",
                'desc': "Game inquiries, services, or general support",
                'emoji': "❓"
            },
            'staff': {
                'label': "Staff Questions",
                'desc': "Feedback, complaints, or staff inquiries",
                'emoji': "👥"
            },
            'partnership': {
                'label': "Partnership Questions",
                'desc': "Cooperation, media, and business inquiries",
                'emoji': "🤝"
            }
        }
    }
}

# --- НАСТРОЙКИ БОТА ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class SupportBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False
        self.config = {} 
        self.active_tickets = {} 
        self.eta_time = "15-30 минут" 
        self.ticket_counter = 1

    async def on_ready(self):
        self.config = self.load_config()
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        self.add_view(MainPanelView())
        
        print(f"Служба поддержки S7 Airlines запущена под именем {self.user}")

    def load_config(self):
        """Загрузка конфигурации и состояния из безопасной папки data"""
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.ticket_counter = data.get("ticket_counter", 1)
                    self.eta_time = data.get("eta_time", "15-30 минут")
                    return {int(k): v for k, v in data.get("guilds", {}).items()}
            except Exception as e:
                print(f"⚠️ Ошибка загрузки конфига: {e}")
        return {}

    def save_config(self):
        """Сохранение конфигурации, счетчика и ETA в безопасную папку data"""
        try:
            payload = {
                "guilds": self.config,
                "ticket_counter": self.ticket_counter,
                "eta_time": self.eta_time
            }
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения конфига: {e}")

bot = SupportBot()

def create_embed(title=None, desc="", footer_text=None, author_user=None, author_role=""):
    """Универсальное создание эмбеда с фирменным цветом бренда S7 и блоком автора"""
    smaller_title_desc = f"### {title}\n{desc}" if title else desc
    
    # ИСПРАВЛЕНИЕ 1: Цвет теперь везде брендовый EMBED_COLOR
    embed = discord.Embed(
        description=smaller_title_desc, 
        color=EMBED_COLOR
    )
    
    if author_user:
        role_label = f" | {author_role}" if author_role else ""
        embed.set_author(
            name=f"{author_user.display_name}{role_label}",
            icon_url=author_user.display_avatar.url,
            url=f"https://discord.com/users/{author_user.id}"
        )
        
    if footer_text:
        embed.set_footer(text=footer_text)
    return embed

# --- СТЕП-БАЙ-СТЕП НАСТРОЙКА /panel ---
class PanelSetupView(discord.ui.View):
    def __init__(self, admin):
        super().__init__(timeout=300)
        self.admin = admin
        self.step = 1
        self.data = {}
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.admin.id:
            await interaction.response.send_message("Эта панель конфигурации вам недоступна.", ephemeral=True)
            return False
        return True

    def update_interface(self, interaction: discord.Interaction):
        self.clear_items()
        guild = interaction.guild

        if self.step == 1:
            select = discord.ui.Select(placeholder="Выберите категорию поддержки...")
            for cat in guild.categories[:25]:
                select.add_option(label=cat.name, value=str(cat.id))
            select.callback = self.save_category
            self.add_item(select)
            return "Шаг 1/4: Выберите **Категорию**, в которой будут создаваться каналы тикетов."

        elif self.step == 2:
            select = discord.ui.Select(placeholder="Выберите категорию для панели...")
            for cat in guild.categories[:25]:
                select.add_option(label=cat.name, value=str(cat.id))
            select.callback = self.save_panel_category
            self.add_item(select)
            return "Шаг 2/4 (Часть 1): Выберите **Категорию**, где находится канал для отправки панели."

        elif self.step == 2.5:
            cat_id = self.data['panel_cat_id']
            category = guild.get_channel(cat_id)
            select = discord.ui.Select(placeholder="Выберите текстовый канал...")
            channels = [ch for ch in category.text_channels][:25]
            if not channels:
                self.step = 2
                return "В выбранной категории нет текстовых каналов! Выберите другую категорию:"
            for ch in channels:
                select.add_option(label=ch.name, value=str(ch.id))
            select.callback = self.save_panel_channel
            self.add_item(select)
            return "Шаг 2/4 (Часть 2): Выберите конкретный **Текстовый канал**, куда прислать панель."

        elif self.step == 3:
            cat_id = self.data['support_cat_id']
            category = guild.get_channel(cat_id)
            select = discord.ui.Select(placeholder="Выберите канал логов...")
            channels = [ch for ch in category.text_channels][:25]
            if not channels:
                channels = [ch for ch in guild.text_channels][:25]
            for ch in channels:
                select.add_option(label=ch.name, value=str(ch.id))
            select.callback = self.save_log_channel
            self.add_item(select)
            return "Шаг 3/4: Выберите **Канал логов** для аудита действий поддержки."

        elif self.step == 4:
            select = discord.ui.Select(placeholder="Выберите роль поддержки...")
            for role in guild.roles[:25]:
                if not role.is_default():
                    select.add_option(label=role.name, value=str(role.id))
            select.callback = self.save_role
            self.add_item(select)
            return "Шаг 4/4: Выберите **Роль поддержки**, сотрудники которой будут видеть тикеты."

        elif self.step == 5:
            ch_id = self.data['panel_channel_id']
            target_channel = guild.get_channel(ch_id)
            
            btn_yes = discord.ui.Button(style=discord.ButtonStyle.success, label="Отправить", emoji="✅")
            btn_no = discord.ui.Button(style=discord.ButtonStyle.danger, label="Отмена", emoji="❌")
            
            btn_yes.callback = self.confirm_setup
            btn_no.callback = self.cancel_setup
            
            self.add_item(btn_yes)
            self.add_item(btn_no)
            return f"Конфигурация завершена. Прислать интерактивную панель в канал {target_channel.mention}?"

    async def save_category(self, interaction: discord.Interaction):
        self.data['support_cat_id'] = int(interaction.data['values'][0])
        self.step = 2
        await interaction.response.edit_message(content=self.update_interface(interaction), view=self)

    async def save_panel_category(self, interaction: discord.Interaction):
        self.data['panel_cat_id'] = int(interaction.data['values'][0])
        self.step = 2.5
        await interaction.response.edit_message(content=self.update_interface(interaction), view=self)

    async def save_panel_channel(self, interaction: discord.Interaction):
        self.data['panel_channel_id'] = int(interaction.data['values'][0])
        self.step = 3
        await interaction.response.edit_message(content=self.update_interface(interaction), view=self)

    async def save_log_channel(self, interaction: discord.Interaction):
        self.data['log_channel_id'] = int(interaction.data['values'][0])
        self.step = 4
        await interaction.response.edit_message(content=self.update_interface(interaction), view=self)

    async def save_role(self, interaction: discord.Interaction):
        self.data['support_role_id'] = int(interaction.data['values'][0])
        self.step = 5
        await interaction.response.edit_message(content=self.update_interface(interaction), view=self)

    async def confirm_setup(self, interaction: discord.Interaction):
        bot.config[interaction.guild.id] = self.data
        bot.save_config()
        target_channel = interaction.guild.get_channel(self.data['panel_channel_id'])
        
        main_panel_embed = discord.Embed(
            title="Support / Клиентская поддержка",
            description="If you wish to open a support request, please press the button below.\n\nЕсли вы желаете открыть обращение в службу поддержки, пожалуйста, нажмите кнопку ниже.",
            color=EMBED_COLOR
        )
        main_panel_view = MainPanelView()
        await target_channel.send(embed=main_panel_embed, view=main_panel_view)
        await interaction.response.edit_message(content="Панель успешно установлена и запущена.", view=None)

    async def cancel_setup(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Настройка отменена администратором.", view=None)


class TopicSelectView(discord.ui.View):
    def __init__(self, lang, callback_func):
        super().__init__(timeout=180)
        self.lang = lang
        self.callback_func = callback_func
        
        t = TRANSLATIONS[lang]
        options = []
        
        for key, data in t['topics'].items():
            emoji_val = data['emoji']
            if ":" in str(emoji_val):
                emoji_val = discord.PartialEmoji.from_str(emoji_val)
                
            options.append(
                discord.SelectOption(
                    label=data['label'],
                    value=key,
                    description=data['desc'],
                    emoji=emoji_val
                )
            )
            
        select = discord.ui.Select(
            placeholder=t['topic_placeholder'],
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        chosen_topic_key = interaction.data['values'][0]
        await self.callback_func(interaction, chosen_topic_key)


# --- ГЛАВНАЯ ПАНЕЛЬ И ВЫБОР ЯЗЫКА И ТЕМЫ ---
class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Request / Открыть обращение", style=discord.ButtonStyle.primary, custom_id="open_request_btn")
    async def open_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.id not in bot.config:
            await interaction.response.send_message("Ошибка: Бот еще не настроен администратором сервера.", ephemeral=True)
            return
            
        if interaction.user.id in bot.active_tickets:
            await interaction.response.send_message("У вас уже есть активная сессия поддержки.", ephemeral=True)
            return

        view = LanguageSelectionView()
        embed = discord.Embed(
            title="Выберите язык | Choose language",
            description="Чтобы наша служба поддержки смогла работать качественнее, пожалуйста, укажите предпочитаемый язык общения.\n\nTo help our customer service provide elite assistance, please select your preferred language.",
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class LanguageSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Русский", style=discord.ButtonStyle.secondary, emoji="🇷🇺")
    async def select_ru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_language(interaction, 'ru')

    @discord.ui.button(label="English", style=discord.ButtonStyle.secondary, emoji="🇬🇧")
    async def select_en(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_language(interaction, 'en')

    async def process_language(self, interaction: discord.Interaction, lang: str):
        user = interaction.user

        async def on_topic_selected(topic_interaction: discord.Interaction, chosen_topic: str):
            bot.active_tickets[user.id] = {
                'guild_id': interaction.guild.id,
                'lang': lang,
                'topic': chosen_topic,
                'status': 'awaiting_description',
                'channel_id': None,
                'agent_id': None,
                'timer_task': None
            }

            await topic_interaction.response.edit_message(
                content=f"⏳ **{TRANSLATIONS[lang]['check_dm_title']}**...\nИнициализируем защищенный канал связи.", 
                embed=None, 
                view=None
            )

            try:
                topic_label = TRANSLATIONS[lang]['topics'][chosen_topic]['label']
                dm_desc = f"**Тема:** {topic_label}\n\n" + TRANSLATIONS[lang]['dm_welcome_desc']
                
                embed = create_embed(
                    title=TRANSLATIONS[lang]['dm_welcome_title'],
                    desc=dm_desc,
                    footer_text=TRANSLATIONS[lang]['footer_bot']
                )
                dm_channel = await user.create_dm()
                await dm_channel.send(embed=embed)
            except discord.Forbidden:
                del bot.active_tickets[user.id]
                await topic_interaction.followup.send("Не удалось отправить сообщение в ЛС. Откройте личные сообщения в настройках конфиденциальности.", ephemeral=True)
                return

            view_dm = discord.ui.View()
            btn_url = discord.ui.Button(label=TRANSLATIONS[lang]['check_dm_btn'], url=f"https://discord.com/channels/@me/{dm_channel.id}")
            view_dm.add_item(btn_url)
            
            await topic_interaction.edit_original_response(
                content=f"**{TRANSLATIONS[lang]['check_dm_title']}**\n{TRANSLATIONS[lang]['check_dm_desc']}", 
                view=view_dm
            )
            
            await asyncio.sleep(20)
            try:
                await topic_interaction.delete_original_response()
            except Exception:
                pass

        topic_view = TopicSelectView(lang, on_topic_selected)
        await interaction.response.edit_message(
            content=None,
            embed=create_embed(title=TRANSLATIONS[lang]['topic_title'], desc=""),
            view=topic_view
        )


# --- КНОПКИ ДЛЯ АГЕНТОВ В ТИКЕТ-КАНАЛЕ ---
class AgentTicketActions(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Принять / Accept", style=discord.ButtonStyle.success, custom_id="accept_ticket")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = bot.active_tickets.get(self.user_id)
        if not ticket or ticket['status'] != 'pending_agent':
            await interaction.response.send_message("Тикет уже обработан.", ephemeral=True)
            return

        ticket['status'] = 'chatting'
        ticket['agent_id'] = interaction.user.id
        lang = ticket['lang']

        if ticket['timer_task']:
            ticket['timer_task'].cancel()
        ticket['timer_task'] = asyncio.create_task(start_inactivity_timer(self.user_id, interaction.channel))

        self.clear_items()
        await interaction.response.edit_message(content=f"**Тикет принят агентом {interaction.user.mention}**", view=None)

        user = bot.get_user(self.user_id)
        if user:
            full_desc = TRANSLATIONS[lang]['accepted_desc'] + TRANSLATIONS[lang]['accepted_instruction']
            
            # ИСПРАВЛЕНИЕ 2: Агент передаётся как профиль с аватаркой в заголовок
            embed = create_embed(
                title=None, 
                desc=full_desc, 
                footer_text=TRANSLATIONS[lang]['footer_agent'],
                author_user=interaction.user,
                author_role=TRANSLATIONS[lang]['accepted_title']
            )
            await user.send(embed=embed)

    @discord.ui.button(label="Отклонить / Reject", style=discord.ButtonStyle.danger, custom_id="reject_ticket")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = bot.active_tickets.get(self.user_id)
        if not ticket or ticket['status'] != 'pending_agent':
            await interaction.response.send_message("Тикет уже обработан.", ephemeral=True)
            return

        lang = ticket['lang']
        user = bot.get_user(self.user_id)
        
        if user:
            embed = create_embed(
                title=TRANSLATIONS[lang]['rejected_title'], 
                desc=TRANSLATIONS[lang]['rejected_desc'], 
                footer_text=TRANSLATIONS[lang]['footer_bot']
            )
            await user.send(embed=embed)

        if ticket['timer_task']:
            ticket['timer_task'].cancel()
        del bot.active_tickets[self.user_id]
        
        await interaction.response.edit_message(content=f"**Тикет отклонен агентом {interaction.user.mention}**", view=None)
        await asyncio.sleep(5)
        await interaction.channel.delete()


# --- ТАЙМЕРЫ И АВТОЗАКРЫТИЕ ---
async def start_inactivity_timer(user_id, channel):
    try:
        await asyncio.sleep(8 * 3600)
        
        ticket = bot.active_tickets.get(user_id)
        if ticket and ticket['status'] == 'chatting':
            lang = ticket['lang']
            user = bot.get_user(user_id)
            if user:
                embed = create_embed(
                    title=TRANSLATIONS[lang]['still_here_title'],
                    desc=TRANSLATIONS[lang]['still_here_desc'] + TRANSLATIONS[lang]['still_here_warning'],
                    footer_text=TRANSLATIONS[lang]['footer_bot']
                )
                await user.send(embed=embed)
                
                log_embed = create_embed(
                    title="⚠️ Ожидание ответа", 
                    desc="> Клиенту отправлено автоматическое уведомление о неактивности. Ожидание завершения: 6 часов.", 
                    footer_text="Система контроля таймингов"
                )
                await channel.send(embed=log_embed)
            
            await asyncio.sleep(6 * 3600)
            await close_ticket_action(user_id, channel, method="timeout")
            
    except asyncio.CancelledError:
        pass

async def close_ticket_action(user_id, channel, method="manual"):
    ticket = bot.active_tickets.get(user_id)
    if not ticket:
        return

    lang = ticket['lang']
    user = bot.get_user(user_id)

    if user:
        desc = TRANSLATIONS[lang]['closed_desc'] + TRANSLATIONS[lang]['closed_footer']
        embed = create_embed(
            title=TRANSLATIONS[lang]['closed_title'], 
            desc=desc, 
            footer_text=TRANSLATIONS[lang]['closed_action_footer']
        )
        await user.send(embed=embed)

    if ticket['timer_task']:
        ticket['timer_task'].cancel()
        
    del bot.active_tickets[user_id]

    reason_key = 'staff_reason_manual' if method == "manual" else 'staff_reason_timeout'
    staff_reason = TRANSLATIONS[lang][reason_key]

    desc_text = TRANSLATIONS[lang]['staff_closed_desc'].format(reason=staff_reason)

    staff_embed = create_embed(
        title=TRANSLATIONS[lang]['staff_closed_title'],
        desc=desc_text,
        footer_text=TRANSLATIONS[lang]['staff_closed_footer']
    )
    await channel.send(embed=staff_embed)


# --- СЛЭШ-КОМАНДЫ ДЛЯ АДМИНИСТРАЦИИ ---
@bot.tree.command(name="panel", description="Запустить интерактивный процесс настройки панели поддержки")
@app_commands.checks.has_permissions(administrator=True)
async def panel_command(interaction: discord.Interaction):
    view = PanelSetupView(interaction.user)
    initial_text = view.update_interface(interaction)
    await interaction.response.send_message(content=initial_text, view=view, ephemeral=True)

@bot.tree.command(name="seteta", description="Изменить ожидаемое время ответа поддержки для клиентов")
@app_commands.checks.has_permissions(manage_messages=True)
async def set_eta(interaction: discord.Interaction, time_val: str):
    bot.eta_time = time_val
    bot.save_config()
    await interaction.response.send_message(f"Ориентировочное время ответа успешно изменено на: **{time_val}**", ephemeral=True)

@bot.tree.command(name="close", description="Закрыть текущую сессию поддержки и зафиксировать тикет")
async def close_command(interaction: discord.Interaction):
    found_user_id = None
    for uid, data in bot.active_tickets.items():
        if data['channel_id'] == interaction.channel.id:
            found_user_id = uid
            break

    if found_user_id:
        await interaction.response.send_message("Запуск процедуры закрытия тикета...", ephemeral=True)
        await close_ticket_action(found_user_id, interaction.channel, method="manual")
    else:
        await interaction.response.send_message("Данный канал не является активным тикетом.", ephemeral=True)


# --- ОБРАБОТКА ВСЕХ СООБЩЕНИЙ (ПЕРЕСЫЛКА ЛС <-> КАНАЛ) ---
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Клиент пишет боту в ЛС
    if isinstance(message.channel, discord.DMChannel):
        ticket = bot.active_tickets.get(message.author.id)
        if not ticket:
            return

        lang = ticket['lang']
        guild = bot.get_guild(ticket['guild_id'])
        cfg = bot.config.get(guild.id)

        # Первое сообщение клиентом (создание текстового канала тикета)
        if ticket['status'] == 'awaiting_description':
            ticket['status'] = 'pending_agent'
            
            formatted_num = f"{bot.ticket_counter:04d}"
            bot.ticket_counter += 1
            bot.save_config()
            
            support_category = guild.get_channel(cfg['support_cat_id'])
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.get_role(cfg['support_role_id']): discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            ticket_channel = await guild.create_text_channel(
                name=f"ticket-{formatted_num}",
                category=support_category,
                overwrites=overwrites
            )
            ticket['channel_id'] = ticket_channel.id

            topic_key = ticket.get('topic', 'general')
            topic_label = TRANSLATIONS[lang]['topics'].get(topic_key, {}).get('label', 'Общий вопрос')

            # ИСПРАВЛЕНИЕ 3: Вместо "Запрос от: ..." в канале агента теперь полноценный профиль клиента с его аватаркой
            agent_embed = create_embed(
                title=None,
                desc=f"**Тема:** {topic_label}\n\n> {message.content}",
                author_user=message.author,
                author_role=TRANSLATIONS[lang]['client_title']
            )
            actions_view = AgentTicketActions(message.author.id)
            await ticket_channel.send(embed=agent_embed, view=actions_view)

            eta_desc = TRANSLATIONS[lang]['ticket_opened_desc'] + TRANSLATIONS[lang]['eta_text'].format(eta=bot.eta_time)
            user_embed = create_embed(
                title=TRANSLATIONS[lang]['ticket_opened_title'], 
                desc=eta_desc, 
                footer_text=TRANSLATIONS[lang]['footer_bot']
            )
            await message.author.send(embed=user_embed)
            return
            
        # Последующие сообщения клиента
        elif ticket['status'] == 'chatting':
            ticket_channel = guild.get_channel(ticket['channel_id'])
            if ticket_channel:
                client_label = TRANSLATIONS[lang]['client_title']
                
                client_embed = create_embed(
                    title=None, 
                    desc=f"> {message.content}", 
                    footer_text="Разговор идет с Customer",
                    author_user=message.author,
                    author_role=client_label
                )
                
                await ticket_channel.send(embed=client_embed)
                await message.add_reaction("✅")
                
                if ticket['timer_task']:
                    ticket['timer_task'].cancel()
                ticket['timer_task'] = asyncio.create_task(start_inactivity_timer(message.author.id, ticket_channel))
                
    # Агент пишет в канал тикета на сервере
    else:
        found_user_id = None
        for uid, data in bot.active_tickets.items():
            if data['channel_id'] == message.channel.id:
                found_user_id = uid
                break

        if found_user_id:
            if message.content.startswith(("/", "!")):
                return

            ticket = bot.active_tickets[found_user_id]
            
            if ticket['status'] != 'chatting':
                return

            lang = ticket['lang']
            user = bot.get_user(found_user_id)
            
            if user:
                embed = create_embed(
                    title=None, 
                    desc=f"> {message.content}", 
                    footer_text=TRANSLATIONS[lang]['footer_agent'],
                    author_user=message.author,
                    author_role=TRANSLATIONS[lang]['accepted_title']
                )
                await user.send(embed=embed)
                
                try:
                    await message.add_reaction("галочка:1234567890")
                except Exception:
                    await message.add_reaction("✅")

# --- ЗАПУСК БОТА ---
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: Переменная окружения 'DISCORD_TOKEN' не найдена!")
