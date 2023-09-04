"""
Copyright (C) 2013 Travis DeWolf

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

'''
Modified by : Kongkiat Rothomphiwat
This softawre is modified version of original software provided by Travis DeWolf.
Modifications have been made to improve the DMP to make it adaptive to moving targets and disturbances.  
'''

import numpy as np
import matplotlib.pyplot as plt


from pydmps.cs import CanonicalSystem


class DMPs(object):
    """Implementation of Dynamic Motor Primitives,
    as described in Dr. Stefan Schaal's (2002) paper."""

    def __init__(
        self, n_dmps, n_bfs, dt=0.01, y0=0, goal=1, goal_vel=0,w=None, ay=None, by=None, **kwargs
    ):
        """
        n_dmps int: number of dynamic motor primitives
        n_bfs int: number of basis functions per DMP
        dt float: timestep for simulation
        y0 list: initial state of DMPs
        goal list: goal state of DMPs
        w list: tunable parameters, control amplitude of basis functions
        ay int: gain on attractor term y dynamics
        by int: gain on attractor term y dynamics
        """

        self.n_dmps = n_dmps
        self.n_bfs = n_bfs
        self.dt = dt
        if isinstance(y0, (int, float)):
            y0 = np.ones(self.n_dmps) * y0
        self.y0 = y0
        if isinstance(goal, (int, float)):
            goal = np.ones(self.n_dmps) * goal
        if isinstance(goal_vel, (int, float)):
            goal_vel = np.ones(self.n_dmps) * goal_vel
        self.goal = goal
        self.goal_vel = goal_vel

        if w is None:
            # default is f = 0
            w = np.zeros((self.n_dmps, self.n_bfs))
        self.w = w

        self.ay = np.ones(n_dmps) * 25.0 if ay is None else ay  # Schaal 2012
        self.by = self.ay / 4.0 if by is None else by  # Schaal 2012

        # set up the CS
        self.cs = CanonicalSystem(dt=self.dt, **kwargs)
        self.timesteps = int(self.cs.run_time / self.dt)

        # set up the DMP system
        self.reset_state()

    def check_offset(self):
        """Check to see if initial position and goal are the same
        if they are, offset slightly so that the forcing term is not 0"""

        for d in range(self.n_dmps):
            if abs(self.y0[d] - self.goal[d]) < 1e-4:
                self.goal[d] += 1e-4

    def gen_front_term(self, x, dmp_num):
        raise NotImplementedError()

    def gen_goal(self, y_des):
        raise NotImplementedError()

    def gen_psi(self):
        raise NotImplementedError()

    def gen_weights(self, f_target):
        raise NotImplementedError()


    def imitate_path(self, y_des, dy_des = None, ddy_des = None, plot=False):
        """Takes in a desired trajectory and generates the set of
        system parameters that best realize this path.

        y_des list/array: the desired trajectories of each DMP
                          should be shaped [n_dmps, run_time]
        """

        # set initial state and goal
        if y_des.ndim == 1:
            y_des = y_des.reshape(1, len(y_des))
        self.y0 = y_des[:, 0].copy()

        self.y_des = y_des.copy()
        self.goal = self.gen_goal(y_des)

        # self.check_offset()

        # generate function to interpolate the desired trajectory
        import scipy.interpolate

        path = np.zeros((self.n_dmps, self.timesteps))
        x = np.linspace(0,  self.cs.run_time , y_des.shape[1])
        

        for d in range(self.n_dmps):
            path_gen = scipy.interpolate.interp1d(x, y_des[d])

            for t in range(self.timesteps):
                path[d, t] = path_gen(t * self.dt)

        y_des = path

        if dy_des is None:
            # calculate velocity of y_des with central differences
            dy_des = np.gradient(y_des, axis=1) / self.dt

        if ddy_des is None:
            # calculate acceleration of y_des with central differences
            ddy_des = np.gradient(dy_des, axis=1) / self.dt


      
        f_target = np.zeros((y_des.shape[1], self.n_dmps))

        # find the force required to move along this trajectory
        for d in range(self.n_dmps):
            f_target[:, d] = ddy_des[d] - self.ay[d] * (
                self.by[d] * (self.goal[d] - y_des[d]) - dy_des[d]
            )

        # efficiently generate weights to realize f_target
        self.gen_weights(f_target)


        if plot is True:
            # plot the basis function activations

            plt.figure()
            plt.subplot(211)
            psi_track = self.gen_psi(self.cs.rollout())
            plt.plot(psi_track)
            plt.title("basis functions")
  
            # plot the desired forcing function vs approx
            for ii in range(self.n_dmps):
                plt.subplot(2, self.n_dmps, self.n_dmps + 1 + ii)
                plt.plot(f_target[:, ii], "*-", label="f_target %i" % ii)

            for ii in range(self.n_dmps):
                f_track =self.gen_front_term(self.cs.rollout(), ii) * np.dot(psi_track, self.w[ii]) / np.sum(psi_track,axis=1)
                plt.subplot(2, self.n_dmps, self.n_dmps + 1 + ii)
                plt.plot(f_track,label="f_track %i" % ii)

                plt.legend()
            plt.title("DMP forcing function")
            plt.tight_layout()

            plt.figure(2)
            
            plt.show()

        self.reset_state()
        return y_des

    def rollout(self, timesteps=None, **kwargs):
        """Generate a system trial, no feedback is incorporated."""

        self.reset_state()

        if timesteps is None:
            if "tau" in kwargs:
                timesteps = int(self.timesteps * kwargs["tau"])
            else:
                timesteps = self.timesteps
    
        # set up tracking vectors
        y_track = np.zeros((timesteps, self.n_dmps))
        dy_track = np.zeros((timesteps, self.n_dmps))
        ddy_track = np.zeros((timesteps, self.n_dmps))

        for t in range(timesteps):

            # run and record timestep
            y_track[t], dy_track[t], ddy_track[t], _= self.step(**kwargs)

        return y_track, dy_track, ddy_track


    def reset_state(self, y0 = None, dy0 = None):
            """Reset the system state"""

            if y0 is not None:
                self.y0 = y0.copy()
                self.y = y0.copy()
            else:
                self.y = self.y0.copy()

            if dy0 is not None:
                self.dy = dy0.copy()
            else:
                self.dy = np.zeros(self.n_dmps)

            self.vel = np.zeros(self.n_dmps)
            self.acc = np.zeros(self.n_dmps)
            self.ddy = np.zeros(self.n_dmps)
            self.cs.reset_state()


    def step(self, tau=1.0, error=0.0, external_force=None, goal = None, goal_vel = None):
        """Run the DMP system for a single timestep.

        tau float: scales the timestep
                   increase tau to make the system execute faster
        error float: optional system feedback
        """

        self.goal = goal if goal is not None else self.goal
        self.goal_vel = goal_vel if goal_vel is not None else self.goal_vel

        error_coupling = 1.0 / (1.0 + abs(error))


        # run canonical system
        # x = self.cs.step(tau=tau, error_coupling=error_coupling)
        x = self.cs.x

        # generate basis function activation
        psi = self.gen_psi(x)

        for d in range(self.n_dmps):

            # generate the forcing term    
            f = self.gen_front_term(x, d) * np.dot(psi, self.w[d]) /  np.sum(psi)

            e_current = self.goal[d] - self.y[d]
            e_dot_current = self.goal_vel[d] - self.vel[d]
           
            # DMP acceleration
            self.ddy[d] = (1-x)*(self.ay[d] * (self.by[d] * e_current + e_dot_current*tau) + f)

            if external_force is not None:
                self.ddy[d] += external_force[d]
            self.ddy[d] /= tau  # z_dot

            self.acc[d] = (self.ddy[d] / tau)

            self.dy[d] += (self.ddy[d] * self.dt) #z 
            self.vel[d] = self.dy[d] / tau 
            
            self.y[d] += self.vel[d] * self.dt

        self.cs.step(tau=tau, error_coupling=error_coupling)

        return self.y, self.vel, self.acc, x