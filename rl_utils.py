from tqdm import tqdm
import numpy as np
import torch
import collections
import random

class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = collections.deque(maxlen=capacity) 

    def add(self, state, action, reward, next_state, done): 
        self.buffer.append((state, action, reward, next_state, done)) 

    def sample(self, batch_size): 
        transitions = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, done = zip(*transitions)
        return np.array(state), action, reward, np.array(next_state), done 

    def size(self): 
        return len(self.buffer)

def moving_average(a, window_size):
    """
    平滑处理列表
    :param a:
    :param window_size:
    :return:
    """
    # 累积
    cumulative_sum = np.cumsum(np.insert(a, 0, 0))
    # 计算每个窗口的均值
    middle = (cumulative_sum[window_size:] - cumulative_sum[:-window_size]) / window_size
    r = np.arange(1, window_size-1, 2)
    # 平滑左边缘
    begin = np.cumsum(a[:window_size-1])[::2] / r
    # 平滑右边缘
    end = (np.cumsum(a[:-window_size:-1])[::2] / r)[::-1]
    return np.concatenate((begin, middle, end))

def train_on_policy_agent(env, agent, num_episodes):
    return_list = []
    for i in range(10):
        with tqdm(total=int(num_episodes/10), desc='Iteration %d' % i) as pbar:
            for i_episode in range(int(num_episodes/10)):
                episode_return = 0
                transition_dict = {'states': [], 'actions': [], 'next_states': [], 'rewards': [], 'dones': []}

                state = env.reset()[0]
                done = False

                while not done:
                    # 获取动作
                    action = agent.take_action(state)
                    # 环境交互
                    next_state, reward, done, *_ = env.step(action)
                    transition_dict['states'].append(state)
                    transition_dict['actions'].append(action)
                    transition_dict['next_states'].append(next_state)
                    transition_dict['rewards'].append(reward)
                    transition_dict['dones'].append(done)
                    state = next_state

                    episode_return += reward

                return_list.append(episode_return)
                # 更新网络参数
                agent.update(transition_dict)

                if (i_episode+1) % 10 == 0:
                    pbar.set_postfix({'episode': '%d' % (num_episodes/10 * i + i_episode+1), 'return': '%.3f' % np.mean(return_list[-10:])})
                pbar.update(1)

    return return_list

def train_off_policy_agent(env, agent, num_episodes, replay_buffer, minimal_size, batch_size):
    """
    离线更新训练
    :param env:
    :param agent:
    :param num_episodes: 训练的episode数
    :param replay_buffer: 数据buffer池
    :param minimal_size: buffer池数量阈值
    :param batch_size:
    :return:
    """
    return_list = []
    for i in range(10):
        with tqdm(total=int(num_episodes/10), desc='Iteration %d' % i) as pbar:
            for i_episode in range(int(num_episodes/10)):
                episode_return = 0
                state = env.reset()[0]
                done = False

                while not done:
                    # 获取动作
                    action = agent.take_action(state)
                    # 环境交互
                    next_state, reward, done, *_ = env.step(action)
                    # buffer池添加数据
                    replay_buffer.add(state, action, reward, next_state, done)
                    state = next_state
                    episode_return += reward

                    if replay_buffer.size() > minimal_size:
                        # 采样batch数据
                        b_s, b_a, b_r, b_ns, b_d = replay_buffer.sample(batch_size)
                        transition_dict = {'states': b_s, 'actions': b_a, 'next_states': b_ns, 'rewards': b_r, 'dones': b_d}
                        # agent更新训练
                        agent.update(transition_dict)

                return_list.append(episode_return)
                if (i_episode+1) % 10 == 0:
                    pbar.set_postfix({'episode': '%d' % (num_episodes/10 * i + i_episode+1), 'return': '%.3f' % np.mean(return_list[-10:])})
                pbar.update(1)
    return return_list


def compute_advantage(gamma, lmbda, td_delta):
    """
    优势函数计算
    :param gamma: 折扣因子
    :param lmbda: 超参，控制步长TD-Error的权重
    :param td_delta: [seq_len, 1] TD-Error
    :return:
    """
    # td error
    td_delta = td_delta.detach().numpy()
    advantage_list = []
    advantage = 0.0
    # 从后递推
    for delta in td_delta[::-1]:
        advantage = gamma * lmbda * advantage + delta
        advantage_list.append(advantage)
    advantage_list.reverse()
    return torch.tensor(advantage_list, dtype=torch.float)
                