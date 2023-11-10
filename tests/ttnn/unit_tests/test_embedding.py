# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.

# SPDX-License-Identifier: Apache-2.0

import pytest
import torch
import ttnn
from tests.ttnn.utils_for_testing import torch_random
from tests.tt_eager.python_api_testing.sweep_tests.common import skip_for_wormhole_b0


def test_base_case(device):
    torch.manual_seed(1234)
    indices = ttnn.to_device(ttnn.from_torch(torch.tensor([[1, 2, 4, 5], [4, 3, 2, 9]]), dtype=ttnn.uint32), device)
    embedding_matrix = ttnn.to_device(ttnn.from_torch(torch.rand(10, 2), dtype=ttnn.bfloat16), device)
    indices_torch = ttnn.to_torch(ttnn.from_device(indices))
    embedding_matrix_torch = ttnn.to_torch(ttnn.from_device(embedding_matrix))
    expected_embeddings = torch.nn.functional.embedding(indices_torch, embedding_matrix_torch)
    embeddings = ttnn.embedding(indices, embedding_matrix)
    assert list(expected_embeddings.shape) == embeddings.shape
    embeddings = ttnn.to_torch(ttnn.from_device(embeddings))
    torch.allclose(expected_embeddings, embeddings, atol=1e-2)


@skip_for_wormhole_b0
@pytest.mark.parametrize("batch_size", [8, 9])
@pytest.mark.parametrize("sentence_size", [32, 512])
@pytest.mark.parametrize("hidden_embedding_dim", [768, 4096])
@pytest.mark.parametrize("vocabulary_size", [512, 30522])
@pytest.mark.parametrize("dtype", [ttnn.bfloat16])
@pytest.mark.parametrize("input_mem_config", [ttnn.DRAM_MEMORY_CONFIG])
@pytest.mark.parametrize("output_mem_config", [ttnn.DRAM_MEMORY_CONFIG])
def test_embedding(
    device,
    batch_size,
    sentence_size,
    hidden_embedding_dim,
    vocabulary_size,
    dtype,
    input_mem_config,
    output_mem_config,
):
    torch.manual_seed(1234)

    torch_input_tensor = torch.randint(0, vocabulary_size - 1, (batch_size, sentence_size))
    torch_weights = torch_random((vocabulary_size, hidden_embedding_dim), -0.1, 0.1, dtype=torch.bfloat16)
    torch_output = torch.nn.functional.embedding(torch_input_tensor, torch_weights)

    input_tensor = ttnn.to_device(ttnn.from_torch(torch_input_tensor), device, memory_config=input_mem_config)
    weights = ttnn.to_device(ttnn.from_torch(torch_weights, dtype=dtype), device, memory_config=input_mem_config)

    output_tensor = ttnn.embedding(input_tensor, weights, memory_config=output_mem_config)
    output_tensor = ttnn.to_layout(output_tensor, ttnn.ROW_MAJOR_LAYOUT)
    output_tensor = ttnn.from_device(output_tensor)
    output_tensor = ttnn.to_torch(output_tensor)

    torch.allclose(torch_output, output_tensor, atol=1e-2)
