import inspect


class StrategyRegister:
    '''
    注册机装饰器
    配合反射使用，可以在配置文件中配置类的初始化。

    初始想法：使用类装饰器是为了维护一个全局生命周期的类属性（当然使用函数做装饰器，然后维护模块全局变量也行）
    类在装饰时，第一步应该是实例化吧。那么类装饰器可以装饰函数么，可以因为对象可调用，具有函数的性质，其call方法即是函数。
    使用类装饰器装饰类时，我们期待其返回应该也是一个类。
    成熟方案，paddlepaddle在用的方案：使用类方法做装饰器，然后维护类的属性。

    '''

    def __init__(self, name=None):
        self._name = name
        self._components = {}

    def add_component(self, obj:callable):
        assert inspect.isclass(obj) or inspect.isfunction(obj), f'被装饰的目标需要是类或者函数，但是传入为：{type(obj)}'
        self._components[obj.__name__] = obj
        return obj

    @property
    def name(self):
        return self._name

    @property
    def components(self):
        return self._components

    def __len__(self):
        return len(self._components.keys())

    def __repr__(self):
        '''
        通过print()，str(),repr()方法可以方便的查看该对象的必要信息，这里给出策略组总名称和策略组已经囊括的策略。
        :return:
        '''
        name = self._name or self.__class__.name
        return f'{name} contains {self._components}'

    def __getitem__(self, item):
        if item not in self._components.keys():
            raise KeyError(f'{item} 不存在，请检查是否正确')
        return self._components[item]


FILTERS = StrategyRegister('filters')
