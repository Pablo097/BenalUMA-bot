import logging, telegram, math
from telegram.ext import CallbackContext
from datetime import datetime, timedelta
from messages.format import get_markdown2_inline_mention
from utils.common import *

logger = logging.getLogger(__name__)

minimum_time_delta = timedelta(milliseconds=100)

def callback_send_message(context):
    message_dict = context.job.context
    chat_id = message_dict['chat_id']
    text = message_dict['text']
    parse_mode = message_dict['parse_mode']
    reply_markup = message_dict['reply_markup']
    # Send messages
    for id in chat_id:
        try:
            context.bot.send_message(id, text, parse_mode,
                                        reply_markup=reply_markup)
        except Exception as e:
            text2 = f"{str(e)}\nMessage could not be sent to user with chat_id {id}"\
                    f" and text:\n{text}"
            logger.warning(text2)
            # Notify is necessary about not delivered messages
            if 'notify_id' in message_dict:
                text = f"🚫 No se ha podido enviar el mensaje a "\
                       f"{get_markdown2_inline_mention(id)}\. 🚫\n"\
                       f"Por favor, si lo ves necesario, contáctale por privado\."
                send_message(context, message_dict['notify_id'], text,
                                            telegram.ParseMode.MARKDOWN_V2)

def send_message(context, chat_id, text, parse_mode=None,
                reply_markup=None, notify_id=None):
    """Send messages without hitting Telegram's flood limit.

    Parameters
    ----------
    context : CallbackContext
        The callback context from the handler from which this function is called.
    chat_id : one int or str, or list of them
        The chat ID of the user(s) to send the message to.
    text : str
        Message to send.
    parse_mode : telegram.ParseMode
        Parse mode, HTML or Markdown (v2). Optional
    reply_markup : telegram.ReplyMarkup
        Reply markup of the message. Optional.
    notify_id : int or str
        chat ID of the user to be notified in case the message(s) could not
        be delivered. Optional

    Returns
    -------
    None
    """
    # Obtain current datetime
    now = datetime.now(madrid)
    # Obtain time for sending the message, preventing flood limit
    if 'next_mq_time' in context.bot_data and now < context.bot_data['next_mq_time']:
        m_time = context.bot_data['next_mq_time']
    else:
        m_time = now
    # Admit unique or list of chat_id's
    if type(chat_id) != list:
        chat_id = [chat_id]

    msgs_per_sec = math.floor(1000000/minimum_time_delta.microseconds)
    # Program message for each user in bursts of messages that fill in a second
    for index in range(math.ceil(len(chat_id)/msgs_per_sec)):
        # Create dictionary with message parameters
        message_dict = {'chat_id': chat_id[index*msgs_per_sec:(index+1)*msgs_per_sec],
                        'text': text,
                        'parse_mode': parse_mode,
                        'reply_markup': reply_markup}
        # If user_id to notify in case of failure is set, add to dict
        if notify_id != None:
            message_dict['notify_id'] = notify_id
        num_chats = len(message_dict['chat_id'])
        # Queue job
        context.job_queue.run_once(callback_send_message, m_time, message_dict,
            name=f"Job ID{chat_id[index*msgs_per_sec]} #{num_chats} Time{m_time}")
        # Increment time for next message
        m_time += minimum_time_delta*num_chats
    # Set minimum time for next message
    context.bot_data['next_mq_time'] = m_time
    return
