# coding=utf-8
# Copyright 2018 The TF-Agents Authors.
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

"""Tests for tf_agents.replay_buffers.replay_buffer."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from tf_agents import specs
from tf_agents.replay_buffers import replay_buffer


class ReplayBufferTestClass(replay_buffer.ReplayBuffer):
  """Basic test for ReplayBuffer subclass."""

  def _add_batch(self, items):
    pass

  def _get_next(self, sample_batch_size, num_steps):
    pass

  def _as_dataset(self, sample_batch_size, num_steps, num_parallel_calls):
    pass

  def _gather_all(self):
    pass

  def _clear(self):
    pass


class ReplayBufferInitTest(tf.test.TestCase):

  def _data_spec(self):
    return [
        specs.TensorSpec([3], tf.float32, 'action'),
        [
            specs.TensorSpec([5], tf.float32, 'lidar'),
            specs.TensorSpec([3, 2], tf.float32, 'camera')
        ]
    ]

  def testReplayBufferInit(self):
    spec = self._data_spec()
    capacity = 10
    rb = ReplayBufferTestClass(spec, capacity)
    self.assertEqual(rb.data_spec, spec)
    self.assertEqual(rb.capacity, capacity)


if __name__ == '__main__':
  tf.test.main()
