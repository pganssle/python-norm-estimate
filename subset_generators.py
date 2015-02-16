"""
Subset generator functions.

Functions which generate sampling subsets on the fly.
"""
import random

class RandomSubsetGenerator:
    """
    Pulls data from the subset in random order, without replacement (e.g. no duplicates)
    """

    def __init__(self, array_subset, n=None, rand_function=None):
        """
        Constructor for the random subset generator. Use a Fischer-Yates shuffle, based on
        the implementation here: http://codegolf.stackexchange.com/a/4820
        
        :param array_subset:
            Provide either an integer or a tuple of of the form (start, end)
        
        :param n:
            The size of the subset to generate (default behavior returns the full array, shuffled)

        :param rand_function:
            A `randint()`-like function.
        """
        if rand_function is None:
            self._randint = random.SystemRandom().randint
        else:
            self._randint = rand_function

        if isinstance(array_subset, (tuple, list)) and len(array_subset) == 2:
            self.low = array_subset[0]
            self.high = array_subset[1]
        else:
            self.low = 0
            self.high = array_subset

        if self.low >= self.high:
            raise ValueError('Array subset must have length >= 0')

        self.index = 0
        self.length = self.high - self.low if n is None else n

        self.high -= 1      # Zero-based index

        self.pool = {}

    def __iter__(self):
        return self

    def next(self):     # Python 2.x support.
        return self.__next__()

    def __next__(self):
        if self.index >= self.length:
            raise StopIteration

        self.index += 1

        i = self._randint(self.low, self.high)
        x = self.pool.get(i, i)         # If i is already there, pick whatever was left in its place
        
        self.pool[i] = self.pool.get(self.low, self.low)  # Swap the low element into place

        self.low += 1

        return x