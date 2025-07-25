"""
A Digital Communications Synchronization 
and PLLs Function Module

A collection of useful functions when studying PLLs
and synchronization and digital comm

Copyright (c) March 2017, Mark Wickert
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of the FreeBSD Project.
"""

import numpy as np
from scipy.signal import lfilter
from logging import getLogger
log = getLogger(__name__)
import warnings


def NDA_symb_sync(z,Ns,L,BnTs,zeta=0.707,I_ord=3):
    """
    zz,e_tau = NDA_symb_sync(z,Ns,L,BnTs,zeta=0.707,I_ord=3)

           z = complex baseband input signal at nominally Ns samples
               per symbol
          Ns = Nominal number of samples per symbol (Ts/T) in the symbol 
               tracking loop, often 4
        BnTs = time bandwidth product of loop bandwidth and the symbol period,
               thus the loop bandwidth as a fraction of the symbol rate.
        zeta = loop damping factor
       I_ord = interpolator order, 1, 2, or 3
    
       e_tau = the timing error e(k) input to the loop filter

          Kp = The phase detector gain in the symbol tracking loop; for the
               NDA algoithm used here always 1
    
    Mark Wickert July 2014

    Motivated by code found in M. Rice, Digital Communications A Discrete-Time 
    Approach, Prentice Hall, New Jersey, 2009. (ISBN 978-0-13-030497-1).
    """
    # Loop filter parameters
    K0 = -1.0 # The modulo 1 counter counts down so a sign change in loop
    Kp = 1.0
    K1 = 4*zeta/(zeta + 1/(4*zeta))*BnTs/Ns/Kp/K0
    K2 = 4/(zeta + 1/(4*zeta))**2*(BnTs/Ns)**2/Kp/K0
    zz = np.zeros(len(z),dtype=np.complex128)
    #zz = np.zeros(int(np.floor(len(z)/float(Ns))),dtype=np.complex128)
    e_tau = np.zeros(len(z))
    #e_tau = np.zeros(int(np.floor(len(z)/float(Ns))))
    #z_TED_buff = np.zeros(Ns)
    c1_buff = np.zeros(2*L+1)

    vi = 0
    CNT_next = 0
    mu_next = 0
    underflow = 0
    epsilon = 0
    mm = 1
    z = np.hstack(([0], z))
    for nn in range(1,Ns*int(np.floor(len(z)/float(Ns)-(Ns-1)))):
        # Define variables used in linear interpolator control
        CNT = CNT_next
        mu = mu_next
        if underflow == 1:
            if I_ord == 1:
                # Decimated interpolator output (piecewise linear)
                z_interp = mu*z[nn] + (1 - mu)*z[nn-1]
            elif I_ord == 2:
                # Decimated interpolator output (piecewise parabolic)
                # in Farrow form with alpha = 1/2
                v2 = 1/2.*np.sum(z[nn+2:nn-1-1:-1]*[1, -1, -1, 1])
                v1 = 1/2.*np.sum(z[nn+2:nn-1-1:-1]*[-1, 3, -1, -1])
                v0 = z[nn]
                z_interp = (mu*v2 + v1)*mu + v0
            elif I_ord == 3:
                # Decimated interpolator output (piecewise cubic)
                # in Farrow form
                v3 = np.sum(z[nn+2:nn-1-1:-1]*[1/6., -1/2., 1/2., -1/6.])
                v2 = np.sum(z[nn+2:nn-1-1:-1]*[0, 1/2., -1, 1/2.])
                v1 = np.sum(z[nn+2:nn-1-1:-1]*[-1/6., 1, -1/2., -1/3.])
                v0 = z[nn]
                z_interp = ((mu*v3 + v2)*mu + v1)*mu + v0
            else:
                log.error('I_ord must 1, 2, or 3')
            # Form TED output that is smoothed using 2*L+1 samples
            # We need Ns interpolants for this TED: 0:Ns-1
            c1 = 0
            for kk in range(Ns):
                if I_ord == 1:
                    # piecewise linear interp over Ns samples for TED
                    z_TED_interp = mu*z[nn+kk] + (1 - mu)*z[nn-1+kk]
                elif I_ord == 2:
                    # piecewise parabolic in Farrow form with alpha = 1/2
                    v2 = 1/2.*np.sum(z[nn+kk+2:nn+kk-1-1:-1]*[1, -1, -1, 1])
                    v1 = 1/2.*np.sum(z[nn+kk+2:nn+kk-1-1:-1]*[-1, 3, -1, -1])
                    v0 = z[nn+kk]
                    z_TED_interp = (mu*v2 + v1)*mu + v0
                elif I_ord == 3:
                    # piecewise cubic in Farrow form
                    v3 = np.sum(z[nn+kk+2:nn+kk-1-1:-1]*[1/6., -1/2., 1/2., -1/6.])
                    v2 = np.sum(z[nn+kk+2:nn+kk-1-1:-1]*[0, 1/2., -1, 1/2.])
                    v1 = np.sum(z[nn+kk+2:nn+kk-1-1:-1]*[-1/6., 1, -1/2., -1/3.])
                    v0 = z[nn+kk]
                    z_TED_interp = ((mu*v3 + v2)*mu + v1)*mu + v0
                else:
                    log.error('Error: I_ord must 1, 2, or 3')
                c1 = c1 + np.abs(z_TED_interp)**2 * np.exp(-1j*2*np.pi/Ns*kk)
            c1 = c1/Ns
            # Update 2*L+1 length buffer for TED output smoothing
            c1_buff = np.hstack(([c1], c1_buff[:-1]))
            # Form the smoothed TED output
            epsilon = -1/(2*np.pi)*np.angle(np.sum(c1_buff)/(2*L+1))
            # Save symbol spaced (decimated to symbol rate) interpolants in zz
            zz[mm] = z_interp
            e_tau[mm] = epsilon # log the error to the output vector e
            mm += 1
        else:
            # Simple zezo-order hold interpolation between symbol samples
            # we just coast using the old value
            #epsilon = 0
            pass
        vp = K1*epsilon       # proportional component of loop filter
        vi = vi + K2*epsilon  # integrator component of loop filter
        v = vp + vi           # loop filter output
        W = 1/float(Ns) + v          # counter control word
       
        # update registers
        CNT_next = CNT - W           # Update counter value for next cycle
        if CNT_next < 0:             # Test to see if underflow has occured
            CNT_next = 1 + CNT_next  # Reduce counter value modulo-1 if underflow
            underflow = 1            # Set the underflow flag
            mu_next = CNT/W          # update mu
        else:
            underflow = 0
            mu_next = mu
    # Remove zero samples at end
    zz = zz[:-(len(zz)-mm+1)]
    # Normalize so symbol values have a unity magnitude
    zz /=np.std(zz)
    e_tau = e_tau[:-(len(e_tau)-mm+1)]
    return zz, e_tau


def DD_carrier_sync(z, M, BnTs, zeta=0.707, mod_type = 'MPSK', type = 0, open_loop = False):
    """
    z_prime,a_hat,e_phi = DD_carrier_sync(z,M,BnTs,zeta=0.707,type=0)
    Decision directed carrier phase tracking
    
           z = complex baseband PSK signal at one sample per symbol
           M = The PSK modulation order, i.e., 2, 8, or 8.
        BnTs = time bandwidth product of loop bandwidth and the symbol period,
               thus the loop bandwidth as a fraction of the symbol rate.
        zeta = loop damping factor
        type = Phase error detector type: 0 <> ML, 1 <> heuristic
    
     z_prime = phase rotation output (like soft symbol values)
       a_hat = the hard decision symbol values landing at the constellation
               values
       e_phi = the phase error e(k) into the loop filter

          Ns = Nominal number of samples per symbol (Ts/T) in the carrier 
               phase tracking loop, almost always 1
          Kp = The phase detector gain in the carrier phase tracking loop; 
               This value depends upon the algorithm type. For the ML scheme
               described at the end of notes Chapter 9, A = 1, K 1/sqrt(2),
               so Kp = sqrt(2).
    
    Mark Wickert July 2014
    Updated for improved MPSK performance April 2020
    Added experimental MQAM capability April 2020

    Motivated by code found in M. Rice, Digital Communications A Discrete-Time 
    Approach, Prentice Hall, New Jersey, 2009. (ISBN 978-0-13-030497-1).
    """
    Ns = 1
    z_prime = np.zeros_like(z)
    a_hat = np.zeros_like(z)
    e_phi = np.zeros(len(z))
    theta_h = np.zeros(len(z))
    theta_hat = 0

    # Tracking loop constants
    Kp = 1 # What is it for the different schemes and modes?
    K0 = 1 
    K1 = 4*zeta/(zeta + 1/(4*zeta))*BnTs/Ns/Kp/K0;
    K2 = 4/(zeta + 1/(4*zeta))**2*(BnTs/Ns)**2/Kp/K0;
    
    # Initial condition
    vi = 0
    # Scaling for MQAM using signal power
    # and known relationship for QAM.
    if mod_type == 'MQAM':
        z_scale = np.std(z) * np.sqrt(3/(2*(M-1)))
        z = z/z_scale
    for nn in range(len(z)):
        # Multiply by the phase estimate exp(-j*theta_hat[n])
        z_prime[nn] = z[nn]*np.exp(-1j*theta_hat)
        if mod_type == 'MPSK':
            if M == 2:
                a_hat[nn] = np.sign(z_prime[nn].real) + 1j*0
            elif M == 4:
                a_hat[nn] = (np.sign(z_prime[nn].real) + \
                             1j*np.sign(z_prime[nn].imag))/np.sqrt(2)
            elif M > 4:
                # round to the nearest integer and fold to nonnegative
                # integers; detection into M-levels with thresholds at mid points.
                a_hat[nn] = np.mod((np.rint(np.angle(z_prime[nn])*M/2/np.pi)).astype(np.int),M)
                a_hat[nn] = np.exp(1j*2*np.pi*a_hat[nn]/M)
            else:
                print('M must be 2, 4, 8, etc.')
        elif mod_type == 'MQAM':
            # Scale adaptively assuming var(x_hat) is proportional to 
            if M ==2 or M == 4 or M == 16 or M == 64 or M == 256:
                x_m = np.sqrt(M)-1
                if M == 2: x_m = 1
                # Shift to quadrant one for hard decisions 
                a_hat_shift = (z_prime[nn] + x_m*(1+1j))/2
                # Soft IQ symbol values are converted to hard symbol decisions
                a_hat_shiftI = np.int16(np.clip(np.rint(a_hat_shift.real),0,x_m))
                a_hat_shiftQ = np.int16(np.clip(np.rint(a_hat_shift.imag),0,x_m))
                # Shift back to antipodal QAM
                a_hat[nn] = 2*(a_hat_shiftI + 1j*a_hat_shiftQ) - x_m*(1+1j)
            else:
                print('M must be 2, 4, 16, 64, or 256');
        if type == 0:
            # Maximum likelihood (ML) Rice
            e_phi[nn] = z_prime[nn].imag * a_hat[nn].real - \
                        z_prime[nn].real * a_hat[nn].imag
        elif type == 1:
            # Heuristic Rice
            e_phi[nn] = np.angle(z_prime[nn]) - np.angle(a_hat[nn])
            # Wrap the phase to [-pi,pi]  
            e_phi[nn] = np.angle(np.exp(1j*e_phi[nn]))
        elif type == 2:
            # Ouyang and Wang 2002 MQAM paper
            e_phi[nn] = np.imag(z_prime[nn]/a_hat[nn])
        else:
            print('Type must be 0 or 1')
        vp = K1*e_phi[nn]      # proportional component of loop filter
        vi = vi + K2*e_phi[nn] # integrator component of loop filter
        v = vp + vi        # loop filter output
        theta_hat = np.mod(theta_hat + v,2*np.pi)
        theta_h[nn] = theta_hat # phase track output array
        if open_loop:
            theta_hat = 0 # for open-loop testing
    
    # Normalize MQAM outputs
    if mod_type == 'MQAM': 
        z_prime *= z_scale
    return z_prime, a_hat, e_phi, theta_h


def time_step(z, ns, t_step, n_step):
    """
    Create a one sample per symbol signal containing a phase rotation
    step Nsymb into the waveform.

    :param z: complex baseband signal after matched filter
    :param ns: number of sample per symbol
    :param t_step: in samples relative to Ns
    :param n_step: symbol sample location where the step turns on
    :return: the one sample per symbol signal containing the phase step

    Mark Wickert July 2014
    """
    z_step = np.hstack((z[:ns * n_step], z[(ns * n_step + t_step):], np.zeros(t_step)))
    return z_step


def phase_step(z, ns, p_step, n_step):
    """
    Create a one sample per symbol signal containing a phase rotation
    step Nsymb into the waveform.

    :param z: complex baseband signal after matched filter
    :param ns: number of sample per symbol
    :param p_step: size in radians of the phase step
    :param n_step: symbol sample location where the step turns on
    :return: the one sample symbol signal containing the phase step

    Mark Wickert July 2014
    """
    nn = np.arange(0, len(z[::ns]))
    theta = np.zeros(len(nn))
    idx = np.where(nn >= n_step)
    theta[idx] = p_step*np.ones(len(idx))
    z_rot = z[::ns] * np.exp(1j * theta)
    return z_rot


def PLL1(theta,fs,loop_type,Kv,fn,zeta,non_lin):
    """
    Baseband Analog PLL Simulation Model

    :param theta: input phase deviation in radians
    :param fs: sampling rate in sample per second or Hz
    :param loop_type: 1, first-order loop filter F(s)=K_LF; 2, integrator
                with lead compensation F(s) = (1 + s tau2)/(s tau1),
                i.e., a type II, or 3, lowpass with lead compensation
                F(s) = (1 + s tau2)/(1 + s tau1)
    :param Kv: VCO gain in Hz/v; note presently assume Kp = 1v/rad
                and K_LF = 1; the user can easily change this
    :param fn: Loop natural frequency (loops 2 & 3) or cutoff
                frquency (loop 1)
    :param zeta: Damping factor for loops 2 & 3
    :param non_lin: 0, linear phase detector; 1, sinusoidal phase detector
    :return: theta_hat = Output phase estimate of the input theta in radians,
             ev = VCO control voltage,
             phi = phase error = theta - theta_hat

    Notes
    -----
    Alternate input in place of natural frequency, fn, in Hz is
    the noise equivalent bandwidth Bn in Hz.


    Mark Wickert, April 2007 for ECE 5625/4625
    Modified February 2008 and July 2014 for ECE 5675/4675
    Python version August 2014
    """
    T = 1/float(fs)
    Kv = 2*np.pi*Kv # convert Kv in Hz/v to rad/s/v

    if loop_type == 1:
        # First-order loop parameters
        # Note Bn = K/4 Hz but K has units of rad/s
        #fn = 4*Bn/(2*pi);
        K = 2*np.pi*fn # loop natural frequency in rad/s
    elif loop_type == 2:
        # Second-order loop parameters
        #fn = 1/(2*pi) * 2*Bn/(zeta + 1/(4*zeta));
        K = 4 *np.pi*zeta*fn # loop natural frequency in rad/s
        tau2 = zeta/(np.pi*fn)
    elif loop_type == 3:
        # Second-order loop parameters for one-pole lowpass with
        # phase lead correction.
        #fn = 1/(2*pi) * 2*Bn/(zeta + 1/(4*zeta));
        K = Kv # Essentially the VCO gain sets the single-sided
                # hold-in range in Hz, as it is assumed that Kp = 1
                # and KLF = 1.
        tau1 = K/((2*np.pi*fn)**2)
        tau2 = 2*zeta/(2*np.pi*fn)*(1 - 2*np.pi*fn/K*1/(2*zeta))
    else:
        warnings.warn('Loop type must be 1, 2, or 3')

    # Initialize integration approximation filters
    filt_in_last = 0; filt_out_last = 0;
    vco_in_last = 0; vco_out = 0; vco_out_last = 0;

    # Initialize working and final output vectors
    n = np.arange(len(theta))
    theta_hat = np.zeros_like(theta)
    ev = np.zeros_like(theta)
    phi = np.zeros_like(theta)

    # Begin the simulation loop
    for k in  range(len(n)):
        phi[k] = theta[k] - vco_out
        if non_lin == 1:
            # sinusoidal phase detector
            pd_out = np.sin(phi[k])
        else:
            # Linear phase detector
            pd_out = phi[k]
        # Loop gain
        gain_out = K/Kv*pd_out # apply VCO gain at VCO
        # Loop filter
        if loop_type == 2:
            filt_in = (1/tau2)*gain_out
            filt_out = filt_out_last + T/2*(filt_in + filt_in_last)
            filt_in_last = filt_in
            filt_out_last = filt_out
            filt_out = filt_out + gain_out
        elif loop_type == 3:
            filt_in = (tau2/tau1)*gain_out - (1/tau1)*filt_out_last
            u3 = filt_in + (1/tau2)*filt_out_last
            filt_out = filt_out_last + T/2*(filt_in + filt_in_last)
            filt_in_last = filt_in
            filt_out_last = filt_out
        else:
            filt_out = gain_out;
        # VCO
        vco_in = filt_out
        if loop_type == 3:
            vco_in = u3
        vco_out = vco_out_last + T/2*(vco_in + vco_in_last)
        vco_in_last = vco_in
        vco_out_last = vco_out
        vco_out = Kv*vco_out # apply Kv
        # Measured loop signals
        ev[k] = vco_in
        theta_hat[k] = vco_out
    return theta_hat, ev, phi


def PLL_cbb(x,fs,loop_type,Kv,fn,zeta):
    """
    Baseband Analog PLL Simulation Model

    :param x: input phase deviation in radians
    :param fs: sampling rate in sample per second or Hz
    :param loop_type: 1, first-order loop filter F(s)=K_LF; 2, integrator
                with lead compensation F(s) = (1 + s tau2)/(s tau1),
                i.e., a type II, or 3, lowpass with lead compensation
                F(s) = (1 + s tau2)/(1 + s tau1)
    :param Kv: VCO gain in Hz/v; note presently assume Kp = 1v/rad
                and K_LF = 1; the user can easily change this
    :param fn: Loop natural frequency (loops 2 & 3) or cutoff
                frequency (loop 1)
    :param zeta: Damping factor for loops 2 & 3
    :return: theta_hat = Output phase estimate of the input theta in radians,
             ev = VCO control voltage,
             phi = phase error = theta - theta_hat

    Mark Wickert, April 2007 for ECE 5625/4625
    Modified February 2008 and July 2014 for ECE 5675/4675
    Python version August 2014
    """
    T = 1/float(fs)
    Kv = 2*np.pi*Kv # convert Kv in Hz/v to rad/s/v

    if loop_type == 1:
        # First-order loop parameters
        # Note Bn = K/4 Hz but K has units of rad/s
        #fn = 4*Bn/(2*pi);
        K = 2*np.pi*fn # loop natural frequency in rad/s
    elif loop_type == 2:
        # Second-order loop parameters
        #fn = 1/(2*pi) * 2*Bn/(zeta + 1/(4*zeta));
        K = 4 *np.pi*zeta*fn # loop natural frequency in rad/s
        tau2 = zeta/(np.pi*fn)
    elif loop_type == 3:
        # Second-order loop parameters for one-pole lowpass with
        # phase lead correction.
        #fn = 1/(2*pi) * 2*Bn/(zeta + 1/(4*zeta));
        K = Kv # Essentially the VCO gain sets the single-sided
                # hold-in range in Hz, as it is assumed that Kp = 1
                # and KLF = 1.
        tau1 = K/((2*np.pi*fn)^2);
        tau2 = 2*zeta/(2*np.pi*fn)*(1 - 2*np.pi*fn/K*1/(2*zeta))
    else:
        warnings.warn('Loop type must be 1, 2, or 3')

    # Initialize integration approximation filters
    filt_in_last = 0; filt_out_last = 0;
    vco_in_last = 0; vco_out = 0; vco_out_last = 0;
    vco_out_cbb = 0

    # Initialize working and final output vectors
    n = np.arange(len(x))
    theta_hat = np.zeros(len(x))
    ev = np.zeros(len(x))
    phi = np.zeros(len(x))

    # Begin the simulation loop
    for k in  range(len(n)):
        #phi[k] = theta[k] - vco_out
        phi[k] = np.imag(x[k] * np.conj(vco_out_cbb))
        pd_out = phi[k]
        # Loop gain
        gain_out = K/Kv*pd_out # apply VCO gain at VCO
        # Loop filter
        if loop_type == 2:
            filt_in = (1/tau2)*gain_out
            filt_out = filt_out_last + T/2*(filt_in + filt_in_last)
            filt_in_last = filt_in
            filt_out_last = filt_out
            filt_out = filt_out + gain_out
        elif loop_type == 3:
            filt_in = (tau2/tau1)*gain_out - (1/tau1)*filt_out_last
            u3 = filt_in + (1/tau2)*filt_out_last
            filt_out = filt_out_last + T/2*(filt_in + filt_in_last)
            filt_in_last = filt_in
            filt_out_last = filt_out
        else:
            filt_out = gain_out;
        # VCO
        vco_in = filt_out
        if loop_type == 3:
            vco_in = u3
        vco_out = vco_out_last + T/2*(vco_in + vco_in_last)
        vco_in_last = vco_in
        vco_out_last = vco_out
        vco_out = Kv*vco_out # apply Kv
        vco_out_cbb = np.exp(1j*vco_out)
        # Measured loop signals
        ev[k] = vco_in
        theta_hat[k] = vco_out
    return theta_hat, ev, phi


#
# Support classes and functions for PLL, AFC, & other Synchronization 
# Development where sample-by-sample processing with states is needed.
#


class NCO:

    def __init__(self, fcenter, fs, kc=1.0, state_init_k: np.unsignedinteger = 0, n_bits: int = 32):
        """
        Implement an n-bit fixed-point NCO for signal generation and tracking loops.

        Parameters
        ----------
        fcenter : Desired NCO center frequency
        fs : Sampling Rate (Hz)
        kc : Gain
        state_init_k : Initial accumulator state, stored as k_hat
        n_bits : Implement n-bit fixed point NCO
        """
        self.n_bits = n_bits
        if n_bits <= 8:
            self.dtype = np.uint8
        elif n_bits <= 16:
            self.dtype = np.uint16
        elif n_bits <= 32:
            self.dtype = np.uint32
        elif n_bits <= 64:
            self.dtype = np.uint64
        else:
            raise NotImplementedError("No dtype implemented for size %d bits" % n_bits)
        self.max_bits_const = self.__max_bits_const__()
        self.fcenter_hat = fcenter
        self.fs = fs
        self.delta_k = self.dtype(np.rint(fcenter * self.max_bits_const) / fs)
        self.kc = kc
        self.k_hat = self.dtype(state_init_k)
        self.k_old = self.dtype(0)

    def __max_bits_const__(self):
        return 2 ** self.n_bits

    def update(self, e_in):
        """
        NCO32_update(e_in)
        Update the NCO 32-bit phase accumulator
        """
        self.k_old = self.k_hat
        self.k_hat = self.dtype(
            np.rint(float(self.k_hat) + float(self.delta_k) + float(self.kc * self.max_bits_const * e_in)))

    def out_sin(self):
        """
        e_out = NCO32_out_sin()
        Output sin(k_hat * fs/2**32)
        """
        e_out = np.sin(2 * np.pi * self.k_hat / self.max_bits_const)
        return e_out

    def out_exp(self):
        """
        e_out = NCO32_out_exp()
        Output exp(j*theta_hat)
        """
        e_out = np.exp(1j * 2 * np.pi * self.k_hat / self.max_bits_const)
        return e_out

    def out_square(self):
        """
        e_out = NCO32_out_square()
        50% duty cycle squarewave
        """
        if self.k_hat >= 0 and self.k_hat < self.dtype(self.max_bits_const >> 1):
            return 1.0
        else:
            return -1.0

    def pos_edge(self, thresh=None):
        """
        edge_bool = NCO32pos-edge(thresh=uint32(2**32 >> 1))
        Output is true on positive edge of NCO_out_square

        :param thresh: If threshold is not provided, ((2**n_bits) >> 1)
        """
        thresh = thresh if thresh else self.dtype(self.max_bits_const >> 1)
        delta_theta = float(self.k_old) - float(self.k_hat)
        if delta_theta > thresh:
            return True
        else:
            return False

    def set_fcenter(self, fcenter_new):
        """
        NCO32_set_fcenter(self, fcenter_new)
        Set a new center frequency in Hz. The actual frequency
        is stored in fcenter_hat.
        """
        self.delta_k = self.dtype(np.rint(fcenter_new*self.max_bits_const/self.fs))
        self.fcenter_hat = self.delta_k/self.max_bits_const*self.fs


class Accumulator(object):
    """
    Initialize an accumulator object with the initial state.
    This accumulator object is for use in DPLL loop filters
    """
    def __init__(self,state = 0.0):
        self.m_state = state


    def update(self, x_in:float):
        """
        accum_update(x_in:float)
        Update the accumulator   
        """
        self.m_state += x_in


    def out(self) -> float:
        """
        y:float = accum_out()
        Formally take the current accumulator value.
        """
        return self.m_state
    

class LoopFilter1(object):

    def __init__(self,alpha2,state = 0.0):
        """

        """
        self.accum = Accumulator(state=state)
        self.alpha2 = alpha2

    
    def filter(self,x):
        """
        y = loop_filter(alpha2, x)
        A 1st-order loop filter for use in AFC tracking loops that
        employ an accumulator with gain constant alpha2 = Ki
        """
        self.accum.update(x)
        y = self.alpha2 * self.accum.out()
        return y
    

class LoopFilter2(object):

    def __init__(self,alpha1,alpha2,state = 0.0):
        """

        """
        self.accum = Accumulator(state=state)
        self.alpha1 = alpha1
        self.alpha2 = alpha2

    
    def filter(self, x):
        """
        y = filter(x)
        A lead-lag DSP loop filter for use in PLL tracking loops.
        """
        self.accum.update(x)
        y = self.alpha1 * x + self.alpha2 * self.accum.out()
        return y
    

def loop_parms1(Bn, kd, fs, bn_mode = True):
    """
        alpha2 = loop_parms1(Bn, kd, fs)
    
    Approximate the noise equivalent bandwidth and the 3dB
    in terms of 1st-order analog lowpass filter. The approximate 
    is good provided Bn << fs. For Bn_mode = False treat Bn
    as f3, the 3dB lowpass bandwidth.
    """
    # fs = 1/(2*pi*RC) = 
    if bn_mode:
        k2 = 1 - np.exp(-4*Bn/fs)
    else:
        k2 = 1 - np.exp(-2*np.pi*Bn/fs)
    kc = 1.0
    return k2/(kc*kd)


def loop_parms2(bn, zeta, kd, fs):
    """
    alpha1, alpha2 = loop_parms2(Bn, zeta, kd, fs)

    Also alpha1 = Kp and alpha2 = Ki is common.
    """
    wn = 2 * bn * (zeta + 1 / (4 * zeta)) ** (-1)
    k1 = 2*zeta*wn/fs + 1/2*(wn/fs)**2
    k2 = (wn/fs)**2
    kc = 1.0
    return k1/(kc*kd), k2/(kc*kd)


# Loop Pull-Out Frequency"
#//////////////////////////////////////////////////////////////////

def loop_pull_out(bn, zeta):
    """
    Delta_f_po = loop_pull_out(Bn, zeta)
    
    2nd-order loop pull-out frequency in Hz from Gardner
    """
    wn = 2 * bn * (zeta + 1 / (4 * zeta)) ** (-1)
    return 1.8*wn*(zeta + 1.0)/(2*np.pi)


# Linear Systems Modeling
#//////////////////////////////////////////////////////////////////

def hetran_v1(k1, k2):
    """
	b, a = Hetran_v1(k1, k2)
    2nd-order DPLL Loop error function He(z) coefficients
    """
    b = [1.0, -2.0, 1.0]
    a = [1.0, -(2.0-k1), (1 - k1 + k2)]
    return b, a


def phi_phase_step(n, bn, zeta, fs=125e6):
    """
    phi = phi_phase_step(n, Bn, zeta, fs=125e6)
    Type 2 DPLL Frequency Step response
    """
    k1, k2 = loop_parms2(bn, zeta, 1.0, fs)
    b, a = hetran_v1(k1, k2)
    print(a)
    phi = np.zeros(len(n))
    for k in range(len(n)):
        phi = 2*np.pi * lfilter(b, a, np.ones(len(n)))
    return phi


def phi_freq_step(n, bn, zeta, fs=125e6):
    """
    phi = phi_freq_step(n, Bn, zeta, fs=125e6)
    Type 2 DPLL Frequency Step response
    """
    k1, k2 = loop_parms2(bn, zeta, 1.0, fs)
    b, a = hetran_v1(k1, k2)
    print(a)
    phi = np.zeros(len(n))
    for k in range(len(n)): # apply a ramp input
        phi = 2*np.pi/fs * lfilter(b, a, n * np.ones(len(n)))
    return phi


def discrim(x):
    """
    function disdata = discrim(x)
    where x is an angle modulated signal in complex baseband form,
    typically centered near f = 0 Hz.

    This is known as the quadri-correlator frequency detector (QCFD) as 
    described in Chapter 5 of Fuyun Ling, "Synchronization in Digital 
    Communications Systems," Cambridge Press, 2017 and elsewhere.
    
    Mark Wickert
    """
    X=np.real(x)        # X is the real part of the received signal
    Y=np.imag(x)        # Y is the imaginary part of the received signal
    b=np.array([1, -1]) # filter coefficients for discrete derivative
    a=np.array([1, 0])  # filter coefficients for discrete derivative
    derY=lfilter(b,a,Y)  # derivative of Y, 
    derX=lfilter(b,a,X)  #    "          X,
    disdata=(X*derY-Y*derX)/(X**2+Y**2)
    return disdata


# Stateful Complex Baseband Discriminator
#//////////////////////////////////////////////////////////////////

class Discriminator(object):

    def __init__(self,f_clk=1.0,state = 0.0 + 0.0j):
        """
        Initialize the discriminator past input complex state.
        This object implements the same algorithm as the function 
        y = discrim(x), but being stateful it can be used in sample
        -by-sample processing such as a component in an AFC tracking loop.

        This is known as the quadri-correlator frequency detector (QCFD) as 
        described in Chapter 5 of Fuyun Ling, "Synchronization in Digital 
        Communications Systems," Cambridge Press, 2017 and elsewhere.

        Mark Wickert November 2024
        """
        self.f_clk = f_clk
        self.state = state


    def update(self, x_in, f_clk_units = True):
        """
        y_d = discrim_update!(discrim1::Discrim, x_in is a complex sample.
        Compute the disciminator output sample and update the state. The ideal 
        discriminator is approximated by virture of the fact that the I/Q
        derivatives are approximated by a single backwards difference.
        """
        der_x_in = x_in - self.state # derivative of x_in (real & imag parts),
        # Normalizing by the squared envelope acts as a limiter too.
        disdata = (x_in.real * der_x_in.imag - x_in.imag * der_x_in.real) / abs(x_in)**2
        self.state = x_in
        if f_clk_units:
            disdata *= self.f_clk/(2*np.pi) # scale the output to frequency
        else:
            disdata /= 2*np.pi # scale the output to normalized frequency
        return disdata


# Pre-built Loops
#//////////////////////////////////////////////////////////////////

#//////////////////////////////////////////////////////////////
# DSP-based PLL tracking loop using the components defined in this module.
#//////////////////////////////////////////////////////////////

def cbb_pll(x_in_pll, bn_pll, k_d, fc_pll=0.0, f_clk_pll=100e3, pll_open=False):
    """
        y_d_pll, y_lf_pll = cbb_PLL(x_in_pll, Bn_pll, k_d, fc_pll=0.0, fclk_pll=100e3, pll_open=False)

    A digital (DSP) complex baseband PLL using components for the NCO and loop filter with accumulator.

    Mark Wickert September 2024
    """
    N_pll = len(x_in_pll)

    PLL_NCO = NCO(fc_pll, f_clk_pll, 1.0, np.uint32(0), n_bits=32)
    x_NCO_pll = np.zeros(N_pll,dtype=complex)
    y_d_pll = np.zeros(N_pll)
    y_lf_pll = np.zeros(N_pll)
    y_lf_pll_old = 0.0
    alpha1_pll, alpha2_pll = loop_parms2(bn_pll, 0.707, 2 * np.pi, f_clk_pll)
    print('PLL (kp, ki) = (%2.3e, %2.3e)' % (alpha1_pll, alpha2_pll))
    pll_lf = LoopFilter2(alpha1_pll, alpha2_pll)
    for k in range(N_pll):
        if pll_open:
            PLL_NCO.update(0.0)
        else:
            PLL_NCO.update(y_lf_pll_old)
        x_NCO_pll[k] = PLL_NCO.out_exp()
        # Phase detector
        y_d_pll[k] = np.imag(x_in_pll[k]*np.conj(x_NCO_pll[k]))
        # y_lf_pll[k] = loop_filter2(lf_accum_pll,alpha1_PLL,alpha2_PLL,k_d*y_d_pll[k])
        y_lf_pll[k] = pll_lf.filter(k_d*y_d_pll[k])
        y_lf_pll_old = y_lf_pll[k]
    return y_d_pll, y_lf_pll, x_NCO_pll


#//////////////////////////////////////////////////////////////
# DSP-based AFC tracking loop using the components defined in this module.
#//////////////////////////////////////////////////////////////

def cbb_afc(x_in_afc, bn_afc, k_d, fc_afc=0.0, f_clk_afc=100e3, afc_open=False):
    """
        y_d_afc, y_lf_afc, x_out_afc = cbb_AFC(x_in_afc, Bn_afc, k_d, fc_afc=0.0, 
                                               f_clk_afc=100e3, afc_open=False)
                                               
    A digital (DSP) complex baseband AFC using components for the NCO Quadricorrelator/
    discriminator and loop filter with accumulator.

    Mark Wickert November 2024
    """
    N_afc = len(x_in_afc)

    AFC_NCO = NCO(fc_afc, f_clk_afc, 1.0, np.uint32(0), n_bits=32)
    discrim_afc = Discriminator(f_clk_afc)
    x_NCO_afc = np.zeros(N_afc,dtype=complex)
    x_out_afc = np.zeros(N_afc,dtype=complex)
    y_d_afc = np.zeros(N_afc)
    y_lf_afc = np.zeros(N_afc)
    alpha2_afc = loop_parms1(bn_afc, 1.0, f_clk_afc)
    print('AFC: ki = %2.3e' % (alpha2_afc,))
    afc_lf = LoopFilter1(alpha2_afc)
    y_lf_afc_old = 0
    # Clock event loop
    for k in range(N_afc):
        if afc_open:
            AFC_NCO.update(0.0)
        else:
            AFC_NCO.update(y_lf_afc_old / f_clk_afc)
        x_NCO_afc[k] = AFC_NCO.out_exp()
        # Frequency Discriminator input mixes input with NCO output conjugated
        # The intent is to frequency translate x_in_afc to 0 Hz
        x_out_afc[k] = x_in_afc[k]*np.conj(x_NCO_afc[k])
        y_d_afc[k] = discrim_afc.update(x_out_afc[k])
        y_lf_afc[k] = afc_lf.filter(y_d_afc[k])
        y_lf_afc_old = y_lf_afc[k]
    return y_d_afc, y_lf_afc, x_out_afc

