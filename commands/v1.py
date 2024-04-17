# Original ELK Bot created by Richard Mongrolle

import os
import json
import discord
import io
import logging
import re
import flag
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from langdetect import detect, DetectorFactory
from googletrans import Translator


logger = logging.getLogger('discord.elkbot.v1')


# -----------------------
# 0.4 - config.json
def load_config():
    with open('./config/v1.json', 'r') as config_file:
        return json.load(config_file)


def save_config(config):
    with open('./config/v1.json', 'w') as config_file:
        json.dump(config, config_file, indent=4)


# -----------------------
# 1.2 - Function to log tasks and send logs to a specified Discord channel
async def log_task(ctx, task_name, details):
    # Log the task with the current timestamp
    logger.debug(f'Channel Name: {ctx.channel.name} - User: {ctx.author.name} - Task: {task_name} - {details}')

    # Send the log to the specified Discord channel
    try:
        log_channel_id = os.getenv('DISCORD_BOT_CHANNEL')
        if not log_channel_id:
            logger.debug(f'Discord bot channel has not been configured')
            return
        log_channel = await ctx.guild.fetch_channel(log_channel_id)
        log_message = f'Legacy command {task_name} called by {ctx.author.mention} in {ctx.channel.mention} with ```{details}```'
        await log_channel.send(log_message, silent=True)
    except Exception as e:
        logger.warning(f'Could not log command to Discord bot channel: {e}')


# ==============================

# 2 - COMMANDS

# 2.1 - Function for checking specific roles by ID
def check_role(ctx):
    # IDs of the roles to check
    # 1182141732079542283 = Kings
    # 1182141804821356644 = Princes
    # 1227613947482472510 = ELK Bot Testing - bot-commands
    role_ids = [1182141732079542283, 1182141804821356644, 1227613947482472510]

    # Check if the command author has any of the specified roles
    return any(role.id in role_ids for role in ctx.author.roles)


# -----------------------
# 2.2 - Configure logging when the bot receives the 'ano' command
@commands.command(name='ano')
@commands.check(check_role)
async def anonymize(ctx):
    """
    Write the message directly by the bot.
    Usage: !ano <Your message>
    """
    command_info = {
        "usage": "!ano <your message here>",
        "description": "Anonymises a message, so it appears to come from the bot rather than you",
    }

    # Help for this command
    if ctx.message.content == '!ano help':
        await ctx.send(f"Description: {command_info['description']}\nUsage: {command_info['usage']}")
        return

    try:
        # Check if the command is in a text channel
        if isinstance(ctx.channel, discord.TextChannel):
            # Delete the message
            await ctx.message.delete()

            # Extract the text after "!ano" and remove leading/trailing spaces
            content_without_command = ctx.message.content[len('!ano'):].strip()

            # Call the log_task function
            await log_task(ctx, 'Anonymize', f'{content_without_command}')

            # Rewrite the message without displaying the command
            await ctx.send(content_without_command)
        pass
    except Exception as e:
        await send_error_to_discord(ctx, str(e))


# -----------------------
# 2.3 - Configure logging when the bot receives the 'delete' command
@commands.command(name='delete')
@commands.check(check_role)
async def delete_messages(ctx, num_messages: int):
    """
    Delete a specified number of messages.
    Usage: !delete <Number messages>
    """
    try:
        # Check if the command is in a text channel
        if isinstance(ctx.channel, discord.TextChannel):
            # Delete the command message
            await ctx.message.delete()

            # Check if the number of messages to delete is greater than 0
            if num_messages > 0:
                # Fetch the last 'num_messages' messages in the channel
                messages = ctx.channel.history(limit=num_messages)

                # Use an async for loop to extract messages from the async generator
                messages_list = []
                async for message in messages:
                    messages_list.append(message)
                    if len(messages_list) == num_messages + 1:
                        break  # Stop after fetching the required number of messages

                # Delete the fetched messages
                for message in messages_list:
                    await message.delete()

                # Call the log_task function
                await log_task(ctx, 'Delete messages', f'{num_messages}')
            else:
                # Send the warning message and delete it after 10 seconds
                await ctx.send("Please provide a valid number of messages to delete (greater than 0).", delete_after=10)
        pass
    except Exception as e:
        await send_error_to_discord(ctx, str(e))


# -----------------------
# 2.4 - Configure logging when the bot receives the 'rewrite' command
@commands.command(name='rewrite')
@commands.check(check_role)
async def rewrite_message(ctx, user_id: int, message_id: int):
    """
    Rewrite a specified message.
    Usage: !rewrite <Member ID> <Message ID>
    """
    try:
        # Check if the command is in a text channel
        if isinstance(ctx.channel, discord.TextChannel):
            # Delete the command message
            await ctx.message.delete()

            try:
                # Fetch the user by ID
                user = await BOT.fetch_user(user_id)

                # Fetch the message with the specified ID
                message = await ctx.channel.fetch_message(message_id)

                # Check if the user and message are found
                if user and message:
                    # Check if the message is sent by the specified user
                    if message.author.id == user.id:
                        # Delete the original message
                        await message.delete()

                        # Send a new message mimicking the original content
                        if message.content:
                            await ctx.send(content=message.content)

                        # Check if the original message has attachments (images)
                        if message.attachments:
                            for attachment in message.attachments:
                                # Download the attachment
                                attachment_content = await attachment.read()

                                # Send the attachment with the new message
                                await ctx.send(
                                    file=discord.File(io.BytesIO(attachment_content), filename=attachment.filename))

                        # Call the log_task function
                        await log_task(ctx, 'Rewrite message', f'User ID: {user.id}, Message ID: {message.id}')
                    else:
                        # Send an error message if the message is not from the specified user
                        await ctx.send("You can only rewrite messages from the specified user.", delete_after=10)
                else:
                    # Send an error message if the user or message is not found
                    await ctx.send("User or message not found.", delete_after=10)
            except discord.NotFound:
                # Send an error message if the user or message is not found
                await ctx.send("User or message not found.", delete_after=10)
        pass
    except Exception as e:
        await send_error_to_discord(ctx, str(e))


# -----------------------
# 2.5 - Switch ON/OFF autotranslation
@commands.command(name='toggletranslation')
@commands.check(check_role)
async def toggle_translation(ctx):
    config = load_config()
    config['translation_enabled'] = not config['translation_enabled']
    save_config(config)
    state = "**enabled**" if config['translation_enabled'] else "**disabled**"
    await ctx.send(f"Automatic translation {state}.")


# ==============================

# 4 - FUNCTIONS

# -----------------------
# 4.1 - Send error messages to a specific Discord logs channel
async def send_error_to_discord(ctx, error_message):
    logger.error(f"Error in `{ctx.channel.name}` by `{ctx.author.name}`:\n{error_message}")

    error_channel_id = os.getenv('DISCORD_BOT_CHANNEL')

    try:
        error_channel = await BOT.fetch_channel(error_channel_id)
        if error_channel:
            await error_channel.send(f"Error in `{ctx.channel.name}` by `{ctx.author.name}`:\n{error_message}")
        else:
            logger.error(f"Can't find the channel {error_channel_id}")
    except Exception as e:
        logger.error(f"Error when trying to send the message: {e}")


BOT = None


async def setup(bot):
    bot.add_command(anonymize)
    bot.add_command(delete_messages)
    bot.add_command(rewrite_message)
    bot.add_command(toggle_translation)

    bot.created_post_id = None

    global BOT
    BOT = bot

    # ==============================

    # 3 - EVENTS

    # -----------------------
    # 3.1 - Sending a private welcome message to new members and in a specific channel

    @bot.event
    async def on_member_join(member):
        # Welcome message for the new users
        welcome_pm = f"# Welcome to the **[ELK] Elements Kingdom server** 🖥️ ! \nHello {member.mention}! We're glad to have you here. 👋 \nIf you have any **problem** or want to be **recruited**, open a ticket (including if you're already in the alliance ingame): https://discord.com/channels/1182139977937723533/1182144002011697203 \nAnd be sure to read our **rules**: https://discord.com/channels/1182139977937723533/1182142923668734062 \nLet's chat! 😄 https://discord.com/channels/1182139977937723533/1182162116308897844"

        # Envoyer le message de bienvenue en message privé au nouveau membre
        await member.send(welcome_pm)

        # ID du channel Discord où envoyer le message de bienvenue
        welcome_channel_id = os.getenv('DISCORD_WELCOME_CHANNEL')

        # Obtenir l'objet channel à partir de l'ID
        welcome_channel = BOT.get_channel(welcome_channel_id)

        # Vérifier si le channel existe et envoyer le message
        if welcome_channel:
            await welcome_channel.send(
                f"Oh, it's you {member.mention}? \n\nCan you see the door, there? Yeah, with a guard in front of. Let's talk to him to **be approved** in our great Kingdom! \nYour next **mission** is to go to https://discord.com/channels/1182139977937723533/1182142923668734062 \n\nIf you have any trouble, you can **contact me directly** with opening a new https://discord.com/channels/1182139977937723533/1182144002011697203 \n\nHave a good day Lord, I hope you will have the favor of the Elements!\n\n.")
        else:
            print(f"Channel not found: {welcome_channel_id}")

    # -----------------------
    # 4.2 - Automatically translate messages if they are not in English
    translator = Translator()

    @bot.event
    async def on_message(message):
        if message.author == BOT.user:
            return

        ctx = await BOT.get_context(message)
        if ctx.valid:
            await BOT.process_commands(message)
            return

        if '-missions' in message.channel.name:
            # Extraction des deux chiffres du nom du canal
            channel_match = re.search(r's(\d{2})-missions', message.channel.name)

            # IF channel = sXX-missions channel
            if channel_match:
                # Création de la mention du groupe
                group_number = channel_match.group(1)
                group_mention = f"@Server {group_number}"
                pattern = r'^Lvl (\d+) (.+)\n(\d{1,2}:\d{2} [apAP][mM]) (\d{2}/\d{2})'
                match = re.match(pattern, message.content)
            else:
                group_mention = ""
                # Expression régulière pour détecter le format spécifique
                pattern = r'^Lvl (\d+) (.+)\n(\d{1,2}:\d{2} [apAP][mM]) (\d{2}/\d{2})'
                match = re.match(pattern, message.content)

            # Trouver l'ID du rôle basé sur le numéro de groupe
            role_number = channel_match.group(1) if channel_match else None
            role_id = None
            if role_number:
                # Recherche du rôle par son nom (par exemple, "Server 01")
                role_name = f"Server {role_number}"
                role = discord.utils.get(message.guild.roles, name=role_name)
                if role:
                    role_id = role.id

            # IF formatting respect standards
            if match:
                # Extraction des données
                level, content, time_str, date_str = match.groups()

                # Obtenir l'année actuelle
                current_year = datetime.now().year

                # Utilisation de zoneinfo pour la conversion en UTC
                time_str = time_str.replace(" UTC", "")
                # Ajouter l'année actuelle lors du parsing de la date et de l'heure
                event_time = datetime.strptime(f"{date_str}/{current_year} {time_str}", '%d/%m/%Y %I:%M %p')
                event_time = event_time.replace(tzinfo=ZoneInfo('UTC'))

                # Générer le temps UNIX
                unix_time = int(event_time.timestamp())

                # Création des timestamps Discord
                timestamp = f"<t:{unix_time}:t>"
                countdown_timestamp = f"<t:{unix_time}:R>"

                # Créer la mention du rôle s'il a été trouvé
                role_mention = f"<@&{role_id}>" if role_id else ""

                # Reformater et envoyer le message
                formatted_message = f"# Lvl {level} {content}\nAt {timestamp}\nIt's {countdown_timestamp}\nReact with ✅ if you will be there, or with ❌ if you can't. If you don't know, use ❓."
                sent_message = await message.channel.send(formatted_message)

                # Ajouter plusieurs réactions au message envoyé
                emojis_to_add = ["✅", "❌", "❓"]  # Liste des emojis à ajouter

                for emoji in emojis_to_add:
                    await sent_message.add_reaction(emoji)  # Ajouter chaque emoji de la liste

                # Créer un fil de discussion à partir du message envoyé
                thread = await sent_message.create_thread(name=f"Lvl {level} {content}", auto_archive_duration=1440)

                # Envoyer un message dans le fil
                await thread.send(role_mention)

                # Supprimer le message initial
                await message.delete()

            else:
                # Traitement normal pour les autres messages
                message_content = message.content

                try:
                    await message.delete()
                except discord.Forbidden as e:
                    error_message = f"Permissions error: {str(e)}"
                    await message.channel.send(error_message)
                    await send_error_to_discord(ctx, error_message)
                    return
                except discord.HTTPException as e:
                    error_message = f"Can't delete message: {str(e)}"
                    await message.channel.send(error_message)
                    await send_error_to_discord(ctx, error_message)
                    return

                try:
                    sent_message = await message.channel.send(message_content)
                    await log_task(ctx, 'Anonymize Message', f'Message ID: {sent_message.id}')
                except discord.HTTPException as e:
                    error_message = f"Can't send new message: {str(e)}"
                    await message.channel.send(error_message)
                    await send_error_to_discord(ctx, error_message)

            return

        # Check if the autotranslation is enabled
        config = load_config()
        if config['translation_enabled']:
            try:
                if len(message.content) > 10:
                    DetectorFactory.seed = 0  # For consistent language detection
                    detected_lang = detect(message.content)

                    # User language roles (considering all roles as potential language codes)
                    user_language_roles = {role.name.lower() for role in message.author.roles}

                    # Check if the detected language matches any of the user's roles
                    if detected_lang in user_language_roles:
                        # Translate the message into English
                        translated = translator.translate(message.content, src=detected_lang, dest='en')
                        flag_emoji = f":flag_{detected_lang}:"
                        await message.reply(f"{flag_emoji} -> :flag_gb: ・ {translated.text}")

            except Exception as e:
                error_message = f"Translation Error: {str(e)}"
                await message.channel.send(error_message)
                await send_error_to_discord(ctx, error_message)

        # Make sure to process other commands even if they are not translated
        await BOT.process_commands(message)

    # -----------------------
    # 4.3 - Manualy translate messages when someone react with a flag

    @bot.event
    async def on_reaction_add(reaction, user):
        # Check if the reaction is a fla
        if len(reaction.emoji) != 2 or user == BOT.user:
            return

        flag_code = flag.dflagize(reaction.emoji)
        flag_match = re.match(r":([A-Z]{2}):", flag_code)

        logger.debug('flag match:', flag_match)

        if not flag_match:
            return

        lang_code = flag_match.group(1)
        original_message = reaction.message

        logger.debug('orig:', original_message.content)

        if lang_code.lower() in ['gb', 'us']:
            lang_code = 'en'

        try:
            translated = translator.translate(original_message.content, src='en', dest=lang_code)
            await original_message.reply(f":flag_gb: -> {reaction.emoji} ・ {translated.text}")
            await reaction.remove(user)
        except Exception as e:
            error_message = f"Translation Error: {str(e)}"
            await original_message.channel.send(error_message)

            ctx = await BOT.get_context(original_message)
            await send_error_to_discord(ctx, error_message)

            raise

    logger.info('Legacy bot loaded')


async def teardown(bot):
    logger.info('Legacy bot unloaded')
