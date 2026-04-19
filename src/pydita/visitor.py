# Base classes for visitor pattern

class Visitor:
    """Abstract class for Visitor

    Visitor instances must define the method visit(object).
    """

    def __str__(self):
        return self.__class__.__name__

    def visit(self, obj: object):
        pass

class Visitable:
    """Base class for objects that can be visited.

    Defines the accept(Visitor) method
    """

    def __str__(self):
        return self.__class__.__name__

    def accept(self, visitor: Visitor) -> None:
        """Applies the visitor to itself.

        Args:
            visitor (Visitor): The visitor doing the visiting.
        """
        visitor.visit(self)
