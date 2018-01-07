class EventHandler:
    __slots__ = ['__registry__']

    def __init__(self):
        self.__registry__ = {}

    def register(self, subscribers):
        for event in subscribers.iterkeys():
            for func in subscribers[event]:
                self.subscribe(event, func)

        return self.__registry__

    def publish(self, event, *args, **kwargs):
        if event in self.__registry__:
            for func in self.__registry__[event]:
                func(*args, **kwargs)

    def subscribe(self, event, func):
        if not callable(func):
            raise TypeError(str(func) + 'is not callable')
        if event in self.__registry__ and type(self.__registry__) is list:
            self.__registry__[event].append(func)
        else:
            self.__registry__[event] = [func]
