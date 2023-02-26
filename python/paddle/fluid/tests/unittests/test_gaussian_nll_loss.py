#   Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import numpy as np

import paddle
import paddle.fluid.core as core
import paddle.nn.functional as F

np.random.seed(10)


def ref_gaussian_nll_loss(
    input, target, var, full=False, eps=1e-6, reduction='none'
):
    if var.shape != input.shape:
        if input.shape[:-1] == var.shape:
            var = np.expand_dims(var, -1)
        elif input.shape[:-1] == var.shape[:-1] and var.shape[-1] == 1:
            pass
        else:
            raise ValueError("var is of incorrect size")
    if reduction != 'none' and reduction != 'mean' and reduction != 'sum':
        raise ValueError(reduction + " is not valid")

    if np.any(var < 0):
        raise ValueError("var has negative entry/entries")

    var = var.copy()
    var = np.clip(var, a_min=eps, a_max=None)

    loss = 0.5 * (np.log(var) + (input - target) ** 2 / var)
    if full:
        loss += 0.5 * np.log(2 * np.pi)

    if reduction == 'none':
        return loss
    elif reduction == 'sum':
        return [np.sum(loss)]
    elif reduction == 'mean':
        return [np.mean(loss)]


class TestGaussianNLLLossAPI(unittest.TestCase):
    # test paddle.nn.functional.gaussian_nll_loss, paddle.nn.gaussian_nll_loss

    def setUp(self, type=None):
        self.shape = [10, 2]
        if type == 'float64':
            self.input_np = np.random.random(self.shape).astype(np.float64)
            self.target_np = np.random.random(self.shape).astype(np.float64)
            self.var_np = np.ones(self.shape).astype(np.float64)
        elif type == 'broadcast':
            self.shape = [10, 2, 3]
            self.broadcast_shape = [10, 2]
            self.input_np = np.random.random(self.shape).astype(np.float32)
            self.target_np = np.random.random(self.shape).astype(np.float32)
            self.var_np = np.ones(self.broadcast_shape).astype(np.float32)
        else:
            self.input_np = np.random.random(self.shape).astype(np.float32)
            self.target_np = np.random.random(self.shape).astype(np.float32)
            self.var_np = np.ones(self.shape).astype(np.float32)

        self.place = (
            paddle.CUDAPlace(0)
            if core.is_compiled_with_cuda()
            else paddle.CPUPlace()
        )

    def test_dynamic_case(self, type=None, full=False, reduction='none'):
        self.setUp(type)
        out_ref = ref_gaussian_nll_loss(
            self.input_np,
            self.target_np,
            self.var_np,
            full=full,
            reduction=reduction,
        )
        paddle.disable_static(self.place)

        input_x = paddle.to_tensor(self.input_np)
        target = paddle.to_tensor(self.target_np)
        var = paddle.to_tensor(self.var_np)
        out1 = F.gaussian_nll_loss(
            input_x, target, var, full=full, reduction=reduction
        )
        gaussian_nll_loss = paddle.nn.GaussianNLLLoss(full, reduction=reduction)
        out2 = gaussian_nll_loss(input_x, target, var)

        for r in [out1, out2]:
            self.assertEqual(
                np.allclose(out_ref, r.numpy(), rtol=1e-5, atol=1e-5), True
            )
        paddle.enable_static()

    def test_static_case(self, type=None, full=False, reduction='none'):
        self.setUp(type)
        out_ref = ref_gaussian_nll_loss(
            self.input_np,
            self.target_np,
            self.var_np,
            full=full,
            reduction=reduction,
        )
        paddle.enable_static()
        with paddle.static.program_guard(paddle.static.Program()):
            if type == 'float64':
                input_x = paddle.static.data('Input_x', self.shape, type)
                target = paddle.static.data('Target', self.shape, type)
                var = paddle.static.data('Var', self.shape, type)
            elif type == 'broadcast':
                input_x = paddle.static.data('Input_x', self.shape)
                target = paddle.static.data('Target', self.shape)
                var = paddle.static.data('Var', self.broadcast_shape)
            else:
                input_x = paddle.static.data('Input_x', self.shape, 'float32')
                target = paddle.static.data('Target', self.shape, 'float32')
                var = paddle.static.data('Var', self.shape, 'float32')
            out1 = F.gaussian_nll_loss(
                input_x, target, var, full=full, reduction=reduction
            )
            gaussian_nll_loss = paddle.nn.GaussianNLLLoss(
                full, reduction=reduction
            )
            out2 = gaussian_nll_loss(input_x, target, var)

            exe = paddle.static.Executor(self.place)
            res = exe.run(
                feed={
                    'Input_x': self.input_np,
                    'Target': self.target_np,
                    'Var': self.var_np,
                },
                fetch_list=[out1, out2],
            )
        for r in res:
            self.assertEqual(
                np.allclose(out_ref, r, rtol=1e-5, atol=1e-5), True
            )

    def test_api(self):
        self.test_dynamic_case('float64')
        self.test_dynamic_case('broadcast')
        self.test_dynamic_case()
        self.test_dynamic_case(full=True, reduction='mean')
        self.test_static_case(full=True, reduction='mean')
        self.test_static_case()
        self.test_static_case('broadcast')
        self.test_static_case('float64')


if __name__ == "__main__":
    unittest.main()
