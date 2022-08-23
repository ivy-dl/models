# global
import os
import ivy
import pytest
import numpy as np

# local
from ivy_models.transformers.helpers import FeedForward, PreNorm
from ivy_models.transformers.perceiver_io import PerceiverIOSpec, PerceiverIO


# Helpers #
# --------#


def test_feedforward(dev_str, f, fw):
    ivy.seed(0)
    feedforward = FeedForward(4, dev_str=dev_str)
    x = ivy.random_uniform(shape=(1, 3, 4), dev_str=dev_str)
    ret = feedforward(x)
    assert list(ret.shape) == [1, 3, 4]


def test_prenorm(dev_str, f, fw):
    ivy.seed(0)
    att = ivy.MultiHeadAttention(4, dev_str=dev_str)
    prenorm = PreNorm(4, att, dev_str=dev_str)
    x = ivy.random_uniform(shape=(1, 3, 4), dev_str=dev_str)
    ret = prenorm(x)
    assert list(ret.shape) == [1, 3, 4]


# Perceiver IO #
# -------------#


@pytest.mark.parametrize("batch_shape", [[1]])
@pytest.mark.parametrize("img_dims", [[224, 224]])
@pytest.mark.parametrize("queries_dim", [1024])
@pytest.mark.parametrize("learn_query", [True])
@pytest.mark.parametrize("load_weights", [True, False])
def test_perceiver_io_img_classification(
    dev_str, f, fw, batch_shape, img_dims, queries_dim, learn_query, load_weights
):

    # params
    input_dim = 3
    num_input_axes = 2
    output_dim = 1000
    network_depth = 8 if load_weights else 1
    num_lat_att_per_layer = 6 if load_weights else 1

    # inputs
    this_dir = os.path.dirname(os.path.realpath(__file__))
    img = ivy.array(
        np.load(os.path.join(this_dir, "img.npy"))[None],
        dtype_str="float32",
        dev_str=dev_str,
    )
    queries = (
        None
        if learn_query
        else ivy.random_uniform(shape=batch_shape + [1, queries_dim], dev_str=dev_str)
    )

    model = PerceiverIO(
        PerceiverIOSpec(
            input_dim=input_dim,
            num_input_axes=num_input_axes,
            output_dim=output_dim,
            queries_dim=queries_dim,
            network_depth=network_depth,
            learn_query=learn_query,
            query_shape=[1],
            num_fourier_freq_bands=64,
            num_lat_att_per_layer=num_lat_att_per_layer,
            device=dev_str,
        )
    )

    # maybe load weights
    if load_weights:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        weight_fpath = os.path.join(
            this_dir,
            "../ivy_models/transformers/pretrained_weights/perceiver_io.pickled",
        )
        assert os.path.isfile(weight_fpath)
        # noinspection PyBroadException
        try:
            v = (
                ivy.Container.from_disk_as_pickled(weight_fpath)
                .from_numpy()
                .as_variables()
            )
        except Exception:
            # If git large-file-storage is not enabled (for example when testing in github actions workflow), then the
            #  test will fail here. A placeholder file does exist, but the file cannot be loaded as pickled variables.
            pytest.skip()
        # noinspection PyUnboundLocalVariable
        assert ivy.Container.identical_structure([model.v, v])

        model = PerceiverIO(
            PerceiverIOSpec(
                input_dim=input_dim,
                num_input_axes=num_input_axes,
                output_dim=output_dim,
                queries_dim=queries_dim,
                network_depth=network_depth,
                learn_query=learn_query,
                query_shape=[1],
                max_fourier_freq=img_dims[0],
                num_fourier_freq_bands=64,
                num_lat_att_per_layer=num_lat_att_per_layer,
                device=dev_str,
            ),
            v=v,
        )

    # output
    output = model(img, queries=queries)

    # cardinality test
    assert output.shape == tuple(batch_shape + [1, output_dim])

    # value test
    if load_weights:

        true_logits = np.array([2.3227594, 3.2260594, 4.682901, 9.067165])
        calc_logits = ivy.to_numpy(output[0, 0])

        def np_softmax(x):
            return np.exp(x) / np.sum(np.exp(x))

        true_indices = np.array([676, 212, 246, 251])
        calc_indices = np.argsort(calc_logits)[-4:]
        assert np.array_equal(true_indices, calc_indices)

        true_probs = np_softmax(true_logits)
        calc_probs = np.take(np_softmax(calc_logits), calc_indices)
        assert np.allclose(true_probs, calc_probs, rtol=0.5)


@pytest.mark.parametrize("batch_shape", [[3]])
@pytest.mark.parametrize("img_dims", [[32, 32]])
@pytest.mark.parametrize("queries_dim", [32])
@pytest.mark.parametrize("learn_query", [True, False])
def test_perceiver_io_flow_prediction(
    dev_str, f, fw, batch_shape, img_dims, queries_dim, learn_query
):
    # params
    input_dim = 3
    num_input_axes = 3
    output_dim = 2

    # inputs
    img = ivy.random_uniform(shape=batch_shape + [2] + img_dims + [3], dev_str=dev_str)
    queries = ivy.random_uniform(shape=batch_shape + img_dims + [32], dev_str=dev_str)

    # model call
    model = PerceiverIO(
        PerceiverIOSpec(
            input_dim=input_dim,
            num_input_axes=num_input_axes,
            output_dim=output_dim,
            queries_dim=queries_dim,
            network_depth=1,
            learn_query=learn_query,
            query_shape=img_dims,
            max_fourier_freq=img_dims[0],
            num_lat_att_per_layer=1,
            device=dev_str,
        )
    )

    # output
    output = model(img, queries=queries)

    # cardinality test
    assert output.shape == tuple(batch_shape + img_dims + [output_dim])
