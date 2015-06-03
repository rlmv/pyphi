#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# convert.py
"""
Conversion functions.
"""

import math
import numpy as np
import logging
from collections import Iterable
import json as _json
from . import __version__

# Create a logger for this module.
log = logging.getLogger(__name__)


# Methods for converting to .json filetype

def get_stamp(obj):
    """Returns a dictionary with the key 'pyphi', containing the object's class
    name and current PyPhi version."""
    return {
        'pyphi': {
            'class': type(obj).__name__,
            'version': __version__
        }
    }


def make_encodable(obj):
    """Return a JSON-encodable representation of an object, recursively using
    any available ``json_dict`` methods, and NumPy's ``tolist`` function for
    arrays."""
    # Use the ``json_dict`` method if available, stamping it with the class
    # name and the current PyPhi version.
    if hasattr(obj, 'json_dict'):
        d = obj.json_dict()
        # Stamp it!
        # TODO stamp?
        # d.update(get_stamp(obj))
        return d
    # If we have numpy data types, convert them to native Python data types.
    elif isinstance(obj, np.int32) or isinstance(obj, np.int64):
        return int(obj)
    elif isinstance(obj, np.float64):
        return float(obj)
    # If we have an array, convert it to a list.
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    # If we have an iterable, recurse on the items. But not for strings, which
    # are reCURSED! (they will recurse forver).
    elif isinstance(obj, Iterable) and not isinstance(obj, str):
        return [make_encodable(item) for item in obj]
    # Otherwise, just return it.
    else:
        return obj


class JSONEncoder(_json.JSONEncoder):

    """
    An extension of the built-in JSONEncoder that can handle native PyPhi
    objects as well as NumPy arrays.

    Uses the ``json_dict`` method for PyPhi objects.
    """

    def encode(self, obj):
        """Encode using the object's ``json_dict`` method if exists, falling
        back on the built-in encoder if not."""
        try:
            return super().encode(make_encodable(obj))
        except AttributeError:
            return super().encode(obj)


def dumps(obj):
    """Serialize ``obj`` to a JSON formatted ``str``."""
    # Use our encoder and compact separators.
    return _json.dumps(obj, cls=JSONEncoder, separators=(',', ':'))


class JSONDecoder(_json.JSONDecoder):

    """
    An extension of the built-in JSONDecoder that can handle native PyPhi
    objects as well as NumPy arrays.
    """
    pass


def loads(s):
    """Deserialize ``s`` (a ``str`` instance containing a JSON document) to a
    PyPhi object."""
    return _json.loads(s)

# Methods for converting nodes and tpms


def nodes2indices(nodes):
    return tuple(n.index for n in nodes) if nodes else ()


def state2holi_index(state):
    """Convert a PyPhi state-tuple to a decimal index according to the **HOLI**
    convention.

    Args:
        state (tuple(int)): A state-tuple where the |ith| element of the tuple
            gives the state of the |ith| node.

    Returns:
        holi_index (``int``): A decimal integer corresponding to a network
            state under the **HOLI** convention.

    Examples:
        >>> from pyphi.convert import state2loli_index
        >>> state2holi_index((1, 0, 0, 0, 0))
        16
        >>> state2holi_index((1, 1, 1, 0, 0, 0, 0, 0))
        224
    """
    return int(''.join(str(int(n)) for n in state), 2)


def state2loli_index(state):
    """Convert a PyPhi state-tuple to a decimal index according to the **LOLI**
    convention.

    Args:
        state (tuple(int)): A state-tuple where the |ith| element of the tuple
            gives the state of the |ith| node.

    Returns:
        loli_index (``int``): A decimal integer corresponding to a network
            state under the **LOLI** convention.

    Examples:
        >>> from pyphi.convert import state2loli_index
        >>> state2loli_index((1, 0, 0, 0, 0))
        1
        >>> state2loli_index((1, 1, 1, 0, 0, 0, 0, 0))
        7
    """
    return int(''.join(str(int(n)) for n in state[::-1]), 2)


def loli_index2state(i, number_of_nodes):
    """Convert a decimal integer to a PyPhi state tuple with the **LOLI**
    convention.

    The output is the reverse of |holi_index2state|.

    Args:
        i (int): A decimal integer corresponding to a network state under the
            **LOLI** convention.

    Returns:
        state (``tuple(int)``): A state-tuple where the |ith| element of the
            tuple gives the state of the |ith| node.

    Examples:
        >>> from pyphi.convert import loli_index2state
        >>> number_of_nodes = 5
        >>> loli_index2state(1, number_of_nodes)
        (1, 0, 0, 0, 0)
        >>> number_of_nodes = 8
        >>> loli_index2state(7, number_of_nodes)
        (1, 1, 1, 0, 0, 0, 0, 0)
    """
    return tuple((i >> n) & 1 for n in range(number_of_nodes))


def holi_index2state(i, number_of_nodes):
    """Convert a decimal integer to a PyPhi state tuple using the **HOLI**
    convention that high-order bits correspond to low-index nodes.

    The output is the reverse of |loli_index2state|.

    Args:
        i (int): A decimal integer corresponding to a network state under the
            **HOLI** convention.

    Returns:
        state (``tuple(int)``): A state-tuple where the |ith| element of the
            tuple gives the state of the |ith| node.

    Examples:
        >>> from pyphi.convert import holi_index2state
        >>> number_of_nodes = 5
        >>> holi_index2state(1, number_of_nodes)
        (0, 0, 0, 0, 1)
        >>> number_of_nodes = 8
        >>> holi_index2state(7, number_of_nodes)
        (0, 0, 0, 0, 0, 1, 1, 1)
    """
    return loli_index2state(i, number_of_nodes)[::-1]


def to_n_dimensional(tpm):
    """Reshape a state-by-node TPM to the N-D form.

    See documentation for the |Network| object for more information on TPM
    formats."""
    # Cast to np.array.
    tpm = np.array(tpm)
    # Get the number of nodes.
    N = tpm.shape[-1]
    # Reshape. We use Fortran ordering here so that the rows use the LOLI
    # convention (low-order bits correspond to low-index nodes). Note that this
    # does not change the actual memory layout (C- or Fortran-contiguous), so
    # there is no performance loss.
    return tpm.reshape([2] * N + [N], order="F").astype(float)


def state_by_state2state_by_node(tpm):
    """Convert a state-by-state TPM to a state-by-node TPM.

    .. note::
        The indices of the rows and columns of the state-by-state TPM are
        assumed to follow the **LOLI** convention. The indices of the rows of
        the resulting state-by-node TPM also follow the **LOLI** convention.
        See the documentation for the |examples| module for more info on these
        conventions.

    Args:
        tpm (list(list) or np.ndarray): A square state-by-state TPM with row
            and column indices following the **LOLI** convention.

    Returns:
        state_by_node_tpm (``np.ndarray``): A state-by-node TPM, with row
            indices following the **LOLI** convention.

    Examples:
        >>> from pyphi.convert import state_by_state2state_by_node
        >>> tpm = np.array([[0.5, 0.5, 0.0, 0.0],
        ...                 [0.0, 1.0, 0.0, 0.0],
        ...                 [0.0, 0.2, 0.0, 0.8],
        ...                 [0.0, 0.3, 0.7, 0.0]])
        >>> state_by_state2state_by_node(tpm)
        array([[[ 0.5,  0. ],
                [ 1. ,  0.8]],
        <BLANKLINE>
               [[ 1. ,  0. ],
                [ 0.3,  0.7]]])
    """
    # Cast to np.array.
    tpm = np.array(tpm)
    # Get the number of states from the length of one side of the TPM.
    S = tpm.shape[-1]
    # Get the number of nodes from the number of states.
    N = int(math.log(S, 2))
    # Initialize the new state-by node TPM.
    sbn_tpm = np.zeros(([2] * N + [N]))
    # Map indices to state-tuples with the LOLI convention.
    states = {i: loli_index2state(i, N) for i in range(S)}
    # Get an array for each node with 1 in positions that correspond to that
    # node being on in the next state, and a 0 otherwise.
    node_on = np.array([[states[i][n] for i in range(S)] for n in range(N)])
    on_probabilities = [tpm * node_on[n] for n in range(N)]
    for i, state in states.items():
        # Get the probability of each node being on given the past state i,
        # i.e., a row of the state-by-node TPM.
        # Assign that row to the ith state in the state-by-node TPM.
        sbn_tpm[state] = [np.sum(on_probabilities[n][i]) for n in range(N)]
    return sbn_tpm


# TODO support nondeterministic TPMs
def state_by_node2state_by_state(tpm):
    """Convert a state-by-node TPM to a state-by-state TPM.

    .. note::
        **A nondeterministic state-by-node TPM can have more than one
        representation as a state-by-state TPM.** However, the mapping can be
        made to be one-to-one if we assume the TPMs to be conditionally
        independent. Therefore, given a nondeterministic state-by-node TPM,
        this function returns the corresponding conditionally independent
        state-by-state.

    .. note::
        The indices of the rows of the state-by-node TPM are assumed to follow
        the **LOLI** convention, while the indices of the columns follow the
        **HOLI** convention. The indices of the rows and columns of the
        resulting state-by-state TPM both follow the **HOLI** convention.

    Args:
        tpm (list(list) or np.ndarray): A state-by-node TPM with row indices
            following the **LOLI** convention and column indices following the
            **HOLI** convention.

    Returns:
        state_by_state_tpm (``np.ndarray``): A state-by-state TPM, with both
            row and column indices following the **HOLI** convention.

    >>> from pyphi.convert import state_by_node2state_by_state
    >>> tpm = np.array([[1, 1, 0],
    ...                 [0, 0, 1],
    ...                 [0, 1, 1],
    ...                 [1, 0, 0],
    ...                 [0, 0, 1],
    ...                 [1, 0, 0],
    ...                 [1, 1, 1],
    ...                 [1, 0, 1]])
    >>> state_by_node2state_by_state(tpm)
    array([[ 0.,  0.,  0.,  1.,  0.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  1.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  0.,  0.,  1.,  0.],
           [ 0.,  1.,  0.,  0.,  0.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  1.,  0.,  0.,  0.],
           [ 0.,  1.,  0.,  0.,  0.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  1.],
           [ 0.,  0.,  0.,  0.,  0.,  1.,  0.,  0.]])
    """
    # Cast to np.array.
    tpm = np.array(tpm)
    # Convert to N-D form.
    tpm = to_n_dimensional(tpm)
    # Get the number of nodes from the last dimension of the TPM.
    N = tpm.shape[-1]
    # Get the number of states.
    S = 2**N
    # Initialize the state-by-state TPM.
    sbs_tpm = np.zeros((S, S))
    if not np.any(np.logical_and(tpm < 1, tpm > 0)):
        # TPM is deterministic.
        for past_state_index in range(S):
            # Use the LOLI convention to get the row and column indices.
            past_state = loli_index2state(past_state_index, N)
            current_state_index = state2loli_index(tpm[past_state])
            sbs_tpm[past_state_index, current_state_index] = 1
    else:
        # TPM is nondeterministic.
        current_state_list = [np.array(loli_index2state(current_state_index, N)) for current_state_index in range(S)]
        for past_state_index in range(S):
            # Use the LOLI convention to get the row and column indices.
            past_state = loli_index2state(past_state_index, N)
            marginal_tpm = tpm[past_state]
            sbs_tpm[past_state_index,:] = [np.prod(marginal_tpm[state == 1]) * np.prod(1-marginal_tpm[state == 0])
                                           for state in current_state_list]
    return sbs_tpm
