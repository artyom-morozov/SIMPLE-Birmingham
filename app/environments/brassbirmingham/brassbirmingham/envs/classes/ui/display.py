
class Display:
    def __init__(self, game=None, env=None, interactive=False, debug_mode=False, policies=None, test=False):
        if game is None:
            if env is None:
                raise RuntimeError("Need to provide display with either game or env")
            self.env = env
        else:
            self.env = env
            self.game = game
        self.interactive = interactive
        self.debug_mode = debug_mode

        self.policies = policies