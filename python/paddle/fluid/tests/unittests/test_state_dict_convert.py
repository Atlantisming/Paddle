# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
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

import paddle
import paddle.nn as nn
import numpy as np
import unittest


class MyModel(nn.Layer):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(100, 300)

    def forward(self, x):
        return self.linear(x)

    @paddle.no_grad()
    def state_dict(
        self,
        destination=None,
        include_sublayers=True,
        structured_name_prefix="",
        use_hook=True,
    ):
        st = super().state_dict(
            destination=destination,
            include_sublayers=include_sublayers,
            structured_name_prefix=structured_name_prefix,
            use_hook=use_hook,
        )
        st["linear.new_weight"] = paddle.transpose(
            st.pop("linear.weight"), [1, 0]
        )
        return st

    @paddle.no_grad()
    def set_state_dict(self, state_dict, use_structured_name=True):
        state_dict["linear.weight"] = paddle.transpose(
            state_dict.pop("linear.new_weight"), [1, 0]
        )
        return super().set_state_dict(state_dict)


def is_state_dict_equal(model1, model2):
    st1 = model1.state_dict()
    st2 = model2.state_dict()
    assert set(st1.keys()) == set(st2.keys())
    for k, v1 in st1.items():
        v2 = st2[k]
        if not np.array_equal(v1.numpy(), v2.numpy()):
            return False
    return True


class TestStateDictConvert(unittest.TestCase):
    def test_main(self):
        model1 = MyModel()
        model2 = MyModel()
        self.assertFalse(is_state_dict_equal(model1, model2))
        model2.set_state_dict(model1.state_dict())
        self.assertTrue(is_state_dict_equal(model1, model2))


if __name__ == "__main__":
    unittest.main()