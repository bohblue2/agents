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

"""Tests for tf_agents.agents.ddpg.ddpg_agent."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf

from tf_agents.agents.ddpg import ddpg_agent
from tf_agents.environments import time_step as ts
from tf_agents.networks import network
from tf_agents.specs import tensor_spec
from tf_agents.utils import common as common_utils

nest = tf.contrib.framework.nest


class DummyActorNetwork(network.Network):
  """Creates an actor network."""

  def __init__(self,
               observation_spec,
               action_spec,
               unbounded_actions=False,
               name=None):
    super(DummyActorNetwork, self).__init__(
        observation_spec=observation_spec,
        action_spec=action_spec,
        state_spec=(),
        name=name)

    self._unbounded_actions = unbounded_actions
    activation = None if unbounded_actions else tf.keras.activations.tanh

    self._single_action_spec = nest.flatten(action_spec)[0]
    self._layer = tf.keras.layers.Dense(
        self._single_action_spec.shape.num_elements(),
        activation=activation,
        kernel_initializer=tf.constant_initializer([2, 1]),
        bias_initializer=tf.constant_initializer([5]),
        name='action')

  def call(self, observations, step_type=(), network_state=()):
    del step_type  # unused.
    observations = tf.to_float(nest.flatten(observations)[0])
    output = self._layer(observations)
    actions = tf.reshape(output,
                         [-1] + self._single_action_spec.shape.as_list())

    if not self._unbounded_actions:
      actions = common_utils.scale_to_spec(actions, self._single_action_spec)

    return nest.pack_sequence_as(self._action_spec, [actions]), network_state


class DummyCriticNetwork(network.Network):

  def __init__(self, observation_spec, action_spec, name=None):
    super(DummyCriticNetwork, self).__init__(
        observation_spec, action_spec, state_spec=(), name=name)

    self._obs_layer = tf.keras.layers.Flatten()
    self._action_layer = tf.keras.layers.Flatten()
    self._joint_layer = tf.keras.layers.Dense(
        1,
        kernel_initializer=tf.constant_initializer([1, 3, 2]),
        bias_initializer=tf.constant_initializer([4]))

  def call(self, observations, actions, step_type=None, network_state=None):
    del step_type
    observations = self._obs_layer(nest.flatten(observations)[0])
    actions = self._action_layer(nest.flatten(actions)[0])
    joint = tf.concat([observations, actions], 1)
    q_value = self._joint_layer(joint)
    q_value = tf.reshape(q_value, [-1])
    return q_value, network_state


class DdpgAgentTest(tf.test.TestCase):

  def setUp(self):
    super(DdpgAgentTest, self).setUp()
    self._obs_spec = [tensor_spec.TensorSpec([2], tf.float32)]
    self._time_step_spec = ts.time_step_spec(self._obs_spec)
    self._action_spec = [tensor_spec.BoundedTensorSpec([1], tf.float32, -1, 1)]

    self._critic_net = DummyCriticNetwork(self._obs_spec, self._action_spec)
    self._bounded_actor_net = DummyActorNetwork(
        self._obs_spec, self._action_spec, unbounded_actions=False)
    self._unbounded_actor_net = DummyActorNetwork(
        self._obs_spec, self._action_spec, unbounded_actions=True)

  def testCreateAgent(self):
    agent = ddpg_agent.DdpgAgent(
        self._time_step_spec,
        self._action_spec,
        actor_network=self._bounded_actor_net,
        critic_network=self._critic_net,
        actor_optimizer=None,
        critic_optimizer=None,
    )
    self.assertTrue(agent.policy() is not None)
    self.assertTrue(agent.collect_policy() is not None)

  def testCriticLoss(self):
    agent = ddpg_agent.DdpgAgent(
        self._time_step_spec,
        self._action_spec,
        actor_network=self._unbounded_actor_net,
        critic_network=self._critic_net,
        actor_optimizer=None,
        critic_optimizer=None,
    )

    observations = [tf.constant([[1, 2], [3, 4]], dtype=tf.float32)]
    time_steps = ts.restart(observations, batch_size=2)

    actions = [tf.constant([[5], [6]], dtype=tf.float32)]

    rewards = tf.constant([10, 20], dtype=tf.float32)
    discounts = tf.constant([0.9, 0.9], dtype=tf.float32)
    next_observations = [tf.constant([[5, 6], [7, 8]], dtype=tf.float32)]
    next_time_steps = ts.transition(next_observations, rewards, discounts)

    expected_loss = 59.6
    loss = agent.critic_loss(time_steps, actions, next_time_steps)

    self.evaluate(tf.global_variables_initializer())
    loss_ = self.evaluate(loss)
    self.assertAllClose(loss_, expected_loss)

  def testActorLoss(self):
    agent = ddpg_agent.DdpgAgent(
        self._time_step_spec,
        self._action_spec,
        actor_network=self._unbounded_actor_net,
        critic_network=self._critic_net,
        actor_optimizer=None,
        critic_optimizer=None,
    )

    observations = [tf.constant([[1, 2], [3, 4]], dtype=tf.float32)]
    time_steps = ts.restart(observations, batch_size=2)

    expected_loss = 4.0
    loss = agent.actor_loss(time_steps)

    self.evaluate(tf.global_variables_initializer())
    loss_ = self.evaluate(loss)
    self.assertAllClose(loss_, expected_loss)

  def testPolicy(self):
    agent = ddpg_agent.DdpgAgent(
        self._time_step_spec,
        self._action_spec,
        actor_network=self._unbounded_actor_net,
        critic_network=self._critic_net,
        actor_optimizer=None,
        critic_optimizer=None,
    )

    observations = [tf.constant([[1, 2]], dtype=tf.float32)]
    time_steps = ts.restart(observations)
    action_step = agent.policy().action(time_steps)
    self.assertEqual(action_step.action[0].shape.as_list(), [1, 1])

    self.evaluate(tf.global_variables_initializer())
    actions_ = self.evaluate(action_step.action)
    self.assertTrue(all(actions_[0] <= self._action_spec[0].maximum))
    self.assertTrue(all(actions_[0] >= self._action_spec[0].minimum))


if __name__ == '__main__':
  tf.test.main()
