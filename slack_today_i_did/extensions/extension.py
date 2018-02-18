import importlib
import types

from slack_today_i_did.generic_bot import BotExtension, ChannelMessage, ChannelMessages
import slack_today_i_did.parser as parser
import slack_today_i_did.text_tools as text_tools


class ExtensionExtensions(BotExtension):
    def _setup_extension(self):
        """ Store disabled tokens in a dict of token: user
            Store disabled extensions in just a list of class names
        """
        self._disabled_tokens = {}
        self._disabled_extensions = []

    def _disabled_message(self, who: str, channel: str) -> ChannelMessages:
        # TODO: this function is currently evaluated in the wrong way by the evaluator
        # so we send the message by hand
        self.send_channel_message(channel, f'This function has been disabled by {who}.')
        return []

    def _flatten_bases(self, cls):
        """ Get all the extensions applied to a bot instance
        """
        bases = cls.__bases__
        known_bases = []

        for base in bases:
            if base.__name__ == 'object':
                continue

            current_bases = self._flatten_bases(base)

            known_bases.append(base)

            if BotExtension in current_bases:
                known_bases.extend(current_bases)

        return known_bases

    def known_functions(self):
        known_functions = BotExtension.known_functions(self)

        try:
            if len(self._disabled_tokens) == 0:
                return known_functions
        except Exception as e:
            return known_functions

        wrapped_functions = {
            k: v for (k, v) in known_functions.items()
            if k not in self._disabled_tokens
        }

        wrapped_functions.update({
            token: lambda *args, **kwargs: self._disabled_message(who, *args, **kwargs)
            for (token, who) in self._disabled_tokens.items()
        })

        return wrapped_functions

    def known_extensions(self, channel: str) -> ChannelMessages:
        """ List all extensions used by the current bot """
        known_bases = list(set(self._flatten_bases(self.__class__)))

        message = 'Currently known extensions:\n'
        message += '\n'.join(base.__name__ for base in known_bases)

        return ChannelMessage(channel, message)

    def tokens_status(self, channel: str) -> ChannelMessages:
        """ Display all the known tokens and if they are enabled """
        known_tokens = [
            (token, token not in self._disabled_tokens) for token in self.known_tokens()
        ]

        message = '\n'.join(f'{token}: {is_enabled}' for (token, is_enabled) in known_tokens)

        return ChannelMessage(channel, message)

    def _manage_extension(self, extension_name: str, is_to_enable: bool, disabler: str) -> None:
        """ Disable or enable an extension, setting who disabled it """
        known_bases = list(set(self._flatten_bases(self.__class__)))
        flipped_tokens = {
            func.__name__: func_alias for (func_alias, func) in self.known_functions().items()
        }

        extensions = [base for base in known_bases if base.__name__ == extension_name]

        for extension in extensions:
            for func in extension.__dict__:
                if func not in flipped_tokens:
                    continue

                if is_to_enable:
                    self._disabled_tokens.pop(flipped_tokens[func], None)
                else:
                    self._disabled_tokens[flipped_tokens[func]] = disabler

            if is_to_enable:
                self._disabled_extensions.remove(extension.__name__)
            else:
                self._disabled_extensions.append(extension.__name__)

    def enable_extension(self, channel: str, extension_name: str) -> ChannelMessages:
        """ enable an extension and all it's exposed tokens by name """
        self._manage_extension(extension_name, is_to_enable=True, disabler=self._last_sender)
        return []

    def disable_extension(self, channel: str, extension_name: str) -> ChannelMessages:
        """ disable an extension and all it's exposed tokens by name """
        self._manage_extension(extension_name, is_to_enable=False, disabler=self._last_sender)
        return []

    def load_extension(self, channel: str, extension_name: str = None) -> ChannelMessages:
        """ Load extensions. By default, load everything.
            Otherwise, load a particular extension
        """
        known_bases = list(set(self._flatten_bases(self.__class__)))
        known_bases_as_str = [base.__name__ for base in known_bases]
        func_names = [func.__name__ for func in self.known_functions().values()]
        meta_funcs = [
            func.__name__ for func in self.known_functions().values() if parser.is_metafunc(func)
        ]

        # make sure to pick up new changes
        importlib.invalidate_caches()

        # import and reload ourselves
        extensions = importlib.import_module(__name__)
        importlib.reload(extensions)

        extension_names = dir(extensions)
        if extension_name is not None and extension_name.strip() != "":
            if extension_name not in extension_names:
                suggestions = [
                    (text_tools.levenshtein(extension_name, name), name) for name in extension_names
                ]

                message = 'No such extension! Maybe you meant one of these:\n'
                message += ' | '.join(name for (_, name) in sorted(suggestions)[:5])
                return ChannelMessage(channel, message)
            else:
                extension_names = [extension_name]

        for extension in extension_names:
            # skip if the extension is not a superclass
            if extension not in known_bases_as_str:
                continue

            extension_class = getattr(extensions, extension)

            for (func_name, func) in extension_class.__dict__.items():
                # we only care about reloading things in our tokens
                if func_name not in func_names:
                    continue

                # ensure that meta_funcs remain so
                if func_name in meta_funcs:
                    func = parser.metafunc(func)

                setattr(self, func_name, types.MethodType(func, self))

        return []

    @parser.metafunc
    def enable_token(self, channel: str, tokens) -> ChannelMessages:
        """ enable tokens """
        for token in tokens:
            if token.func_name in self._disabled_tokens:
                self._disabled_tokens.pop(token.func_name, None)
        return []

    @parser.metafunc
    def disable_token(self, channel: str, tokens) -> ChannelMessages:
        """ disable tokens """
        for token in tokens:
            func_name = token.func_name
            self._disabled_tokens[func_name] = self._last_sender

        return []
