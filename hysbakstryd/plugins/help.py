from . import Plugin


class HelpPlugin(Plugin):

    """
    Show help on registered plugins.

    Offers two commands:
     * `help_plugins`: return to the calling client a list of plugins, or, when called
       with a `plugin` argument, return the documentation on the loaded plugin.
     * `help_command`: return to the calling client a list of commands, or, when called
       with a `command` argument, return the documentation of the given command.
    """

    def do_WHAT_DO_I_DO_NOW(self, client):
        """Return a soothing help message."""

        message = """
        Don't panic!
        """

        return (), ('relax', message), None

    def do_help(self, client):
        """
        Return some help on what to do next.
        """
        
        message = """
First things first: If you don't know what to do, call the WHAT_DO_I_DO_NOW command.

Here is a list of all commands that are available on this server:
{}

call help_command with command=<command name> for each of these to find out what
each of them does.

It's probably best to start with movement, so try this first:
  ``set_level, level=5``
  ``set_direction, direction="up"``
then wait a little while and get your state with:
  ``get_state``
"""
        commandlist = '\n'.join(sorted(self.game.command_map.keys()))
        
        return (), ('help', message.format(commandlist)), None

    def do_help_plugin(self, client, plugin=None):
        """
        Return a list of plugins or documentation on a specific plugin (if given).
        """
        if not plugin:
            return (), ('help_for_plugins', [p.__class__.__name__ for p in self.game.plugins]), None

        plc = [p for p in self.game.plugins if p.__class__.__name__ == plugin]
        if plc:
            p = plc[0]
            return (), ('help_for_plugin', p.__doc__), None

        return (), None, None

    def do_help_command(self, client, command=None):
        """
        Return a list of available commands or documentation on a specific command.
        """
        if not command:
            return (), ('help_for_commands', list(self.game.command_map.keys())), None

        if command in self.game.command_map:
            return (), ('help_for_command', self.game.command_map[command].__doc__), None

        return (), ('help_for_command', 'command not found'), None
