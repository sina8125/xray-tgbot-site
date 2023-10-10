import json
from typing import Optional, Dict, cast

from asgiref.sync import sync_to_async
from telegram.ext import BasePersistence, PersistenceInput, PicklePersistence
from telegram.ext._utils.types import BD, CD, UD, CDCData, ConversationDict, ConversationKey

from django_PTB_persistence.models import UserData, ChatData, BotData, CallbackData, ConversationData


class DjangoPersistence(BasePersistence[UD, CD, BD]):
    def __init__(
            self,
            namespace: str = "",
            store_data: Optional[PersistenceInput] = None,
            update_interval: float = 60,

    ):
        super().__init__(
            store_data=store_data,
            update_interval=update_interval
        )
        self._namespace = namespace

    async def get_user_data(self) -> Dict[int, UD]:
        user_data_list = await sync_to_async(list)(UserData.objects.filter(namespace=self._namespace))
        return {data.user_id: data.data for data in user_data_list}

    async def get_chat_data(self) -> Dict[int, CD]:
        chat_data_list = await sync_to_async(list)(ChatData.objects.filter(namespace=self._namespace))
        return {data.chat_id: data.data for data in chat_data_list}

    async def get_bot_data(self) -> BD:
        try:
            return (await BotData.objects.aget(namespace=self._namespace)).data
        except BotData.DoesNotExist:
            return {}

    async def get_callback_data(self) -> Optional[CDCData]:
        try:
            callback_data = (await CallbackData.objects.aget(namespace=self._namespace)).data
            return cast(CDCData, ([(one, float(two), three) for one, two, three in callback_data[0]], callback_data[1]))
        except CallbackData.DoesNotExist:
            return None

    async def get_conversations(self, name: str) -> ConversationDict:
        conversation_data_list = await sync_to_async(list)(
            ConversationData.objects.filter(namespace=self._namespace, name=name)
        )
        return {
            tuple(json.loads(data.key)): data.state for data in conversation_data_list
        }

    async def update_conversation(
            self, name: str, key: ConversationKey, new_state: Optional[object]
    ) -> None:
        await ConversationData.objects.aupdate_or_create(
            namespace=self._namespace,
            name=name,
            key=json.dumps(key, sort_keys=True),
            defaults={'state': new_state}
        )

    async def update_user_data(self, user_id: int, data: UD) -> None:
        await UserData.objects.aupdate_or_create(
            namespace=self._namespace,
            user_id=user_id,
            defaults={'data': data}
        )

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        await ChatData.objects.aupdate_or_create(
            namespace=self._namespace,
            chat_id=chat_id,
            defaults={'data': data}
        )

    async def update_bot_data(self, data: BD) -> None:
        await BotData.objects.aupdate_or_create(
            namespace=self._namespace,
            defaults={'data': data}
        )

    async def update_callback_data(self, data: CDCData) -> None:
        await CallbackData.objects.aupdate_or_create(
            namespace=self._namespace,
            defaults={'data': data}
        )

    async def drop_chat_data(self, chat_id: int) -> None:
        try:
            (await ChatData.objects.aget(
                namespace=self._namespace,
                chat_id=chat_id
            )).delete()
        except ChatData.DoesNotExist:
            pass

    async def drop_user_data(self, user_id: int) -> None:
        try:
            (await UserData.objects.aget(
                namespace=self._namespace,
                user_id=user_id
            )).delete()
        except UserData.DoesNotExist:
            pass

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        try:
            if isinstance(user_data, dict):
                orig_keys = set(user_data.keys())
                user_data.update((await UserData.objects.aget(namespace=self._namespace, user_id=user_id)).data)
                for key in orig_keys - set(user_data.keys()):
                    user_data.pop(key)
        except UserData.DoesNotExist:
            pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        try:
            if isinstance(chat_data, dict):
                orig_keys = set(chat_data.keys())
                chat_data.update((await ChatData.objects.aget(namespace=self._namespace, chat_id=chat_id)).data)
                for key in orig_keys - set(chat_data.keys()):
                    chat_data.pop(key)
        except ChatData.DoesNotExist:
            pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        try:
            if isinstance(bot_data, dict):
                orig_keys = set(bot_data.keys())
                bot_data.update((await BotData.objects.aget(namespace=self._namespace)).data)
                for key in orig_keys - set(bot_data.keys()):
                    bot_data.pop(key)
        except BotData.DoesNotExist:
            pass

    async def flush(self) -> None:
        pass
