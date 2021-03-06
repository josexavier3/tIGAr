"""
The ``timeIntegration`` module
------------------------------
is not strictly related to IGA, but contains routines for time integration
methods commonly used in conjunction with IGA, that we found convenient for 
implementing demos.
"""

from tIGAr.common import *

class BackwardEulerIntegrator:

    """
    Class to encapsulate backward Euler formulas for first- and second-order
    ODE systems.  
    """

    def __init__(self,DELTA_T,x,oldFunctions,t=0.0):
        """
        Initialize a backward Euler integrator with time step ``DELTA_T``.
        The unknown function is ``x``.  The sequence of ``Function``
        objects ``oldFunctions`` provides data from the previous time step.
        If ``oldFunctions`` contains only one ``Function``, then the system
        is assumed to be of order 1 and that function is interpreted as the
        initial value of ``x``.  If ``oldFunctions`` contains an additional
        element, then the ODE system is assumed to be of second order, and
        this additional element is interpreted as the initial velocity.
        The parameter ``t`` is the initial time, and defaults to zero.
        """
        self.systemOrder = len(oldFunctions)
        self.DELTA_T = DELTA_T
        self.x = x
        self.x_old = oldFunctions[0]
        if(self.systemOrder == 2):
            self.xdot_old = oldFunctions[1]
        self.t = t + float(DELTA_T) # DELTA_T may be a Constant already
            
    def xdot(self):
        """
        Returns the approximation of the velocity at the current time step.
        """
        return Constant(1.0/self.DELTA_T)*self.x \
            - Constant(1.0/self.DELTA_T)*self.x_old

    def xddot(self):
        """
        Returns the approximation of the acceleration at the current time
        step.
        """
        return Constant(1.0/self.DELTA_T)*self.xdot() \
            - Constant(1.0/self.DELTA_T)*self.xdot_old
            
    def advance(self):
        """
        Overwrites the data from the previous time step with the
        data from the current time step.
        """
        x_old = Function(self.x.function_space())
        x_old.assign(self.x)
        if(self.systemOrder==2):
            xdot_old = Function(self.x.function_space())
            xdot_old.assign(self.xdot())
        self.x_old.assign(x_old)
        if(self.systemOrder==2):
            self.xdot_old.assign(xdot_old)
        self.t += float(self.DELTA_T)

class LoadStepper:

    """
    Time "integrator" for a problem with no time derivatives.  This 
    is basically just to keep track of a parameter, ``self.t``, that
    can be used to parameterize external loading.
    """

    def __init__(self,DELTA_T,t=0.0):
        """
        Initializes the ``LoadStepper`` with a (pseudo)time step ``DELTA_T``
        and initial time ``t``, which defaults to zero.
        """
        self.DELTA_T = DELTA_T
        self.tval = t
        self.t = Expression("t",t=self.tval,degree=0)
        self.advance()

    def advance(self):
        """
        Increments the loading.
        """
        self.tval += float(self.DELTA_T)
        self.t.t = self.tval
        
def x_alpha(alpha, x, x_old):
    """
    Returns an ``alpha``-level quantity, given current and old values,
    i.e., ``Constant(alpha)*x + Constant(1.0-alpha)*x_old``.
    """
    return Constant(alpha)*x + Constant(1.0-alpha)*x_old

class GeneralizedAlphaIntegrator:

    """
    Class encapsulating all of the formulas for generalized-alpha time
    integration, for both first-order and second-order ODE systems.
    """
    
    def __init__(self,RHO_INF,DELTA_T,x,oldFunctions,t=0.0,
                 useFirstOrderAlphaM=False):
        """
        Sets up a time integrator with spectral radius
        ``RHO_INF`` in the limit of time step ``DELTA_T`` going to
        zero.  The unknown ``Function`` is ``x``, and a sequence of 
        ``Function`` objects, ``oldFunctions``, provide data from 
        the previous time step.
        If ``oldFunctions`` contains two functions, then these are 
        interpreted as the previous time step's solution and velocity, and 
        the ODE system is assumed to be of first order.  If a third 
        ``Function`` is provided, it is assumed to be the acceleration, and
        the ODE system is assumed to be of second order.  
        The optimal damping parameters for the first order case can optionally
        be used with second-order systems (as one might do, e.g., to
        optimally damp a first-order subproblem), by passing the non-default
        parameter value ``useFirstOrderAlphaM=True``.  
        The parameter ``t`` is the initial time, and defaults to zero.

        NOTE: This includes the implicit midpoint rule as a special case, 
        i.e., ``RHO_INF=1.0``.

        NOTE: Specifying the initial velocity and acceleration of second-order
        problem over-determines it.  The initial acceleration should be set
        in a way that is compatible with the other initial data and the
        governing equation.
        """
        self.RHO_INF = RHO_INF
        self.DELTA_T = DELTA_T
        # infer whether this is a first or second-order ODE system based on
        # the number of functions prescribed for the previous time step
        self.systemOrder = len(oldFunctions)-1
        # always use first-order alpha_m for first order systems, and
        # optionally use it for second-order systems (e.g., in yuri's fsi
        # paper)
        if(useFirstOrderAlphaM or self.systemOrder==1):
            self.ALPHA_M = 0.5*(3.0 - RHO_INF)/(1.0 + RHO_INF)
        else:
            self.ALPHA_M = (2.0 - RHO_INF)/(1.0 + RHO_INF)
        self.ALPHA_F = 1.0/(1.0 + RHO_INF)
        self.GAMMA = 0.5 + self.ALPHA_M - self.ALPHA_F
        self.BETA = 0.25*(1.0 + self.ALPHA_M - self.ALPHA_F)**2
        self.x = x
        self.x_old = oldFunctions[0]
        self.xdot_old = oldFunctions[1]
        if(self.systemOrder == 2):
            self.xddot_old = oldFunctions[2]
        self.t = t + float(DELTA_T) # DELTA_T may be a Constant already
            
    def xdot(self):
        """
        Returns the current time derivative of the solution at the ``n+1``
        level, as a linear combination of the current solution and 
        data from the previous time step.
        """
        if(self.systemOrder == 1):
            return Constant(1.0/(self.GAMMA*self.DELTA_T))*self.x\
                + Constant(-1.0/(self.GAMMA*self.DELTA_T))*self.x_old\
                + Constant((self.GAMMA-1.0)/self.GAMMA)*self.xdot_old
        else:
            return Constant(self.GAMMA/(self.BETA*self.DELTA_T))*self.x\
                + Constant(-self.GAMMA/(self.BETA*self.DELTA_T))*self.x_old\
                + Constant(1.0 - self.GAMMA/self.BETA)*self.xdot_old\
                + Constant((1.0-self.GAMMA)*self.DELTA_T \
                           - (1.0 - 2.0*self.BETA)*self.DELTA_T\
                           *self.GAMMA/(2.0*self.BETA))*self.xddot_old

    def xddot(self):
        """
        Returns the current 2nd time derivative of the solution at the ``n+1``
        level, as a linear combination of the current solution and 
        data from the previous time step.
        """
        # should never be used for first-order systems
        return Constant(1.0/self.DELTA_T/self.GAMMA)*self.xdot()\
            + Constant(-1.0/self.DELTA_T/self.GAMMA)*self.xdot_old\
            + Constant(-(1.0-self.GAMMA)/self.GAMMA)*self.xddot_old

    def x_alpha(self):
        """
        Returns the alpha-level solution.
        """
        return x_alpha(self.ALPHA_F,self.x,self.x_old)
    
    def xdot_alpha(self):
        """
        Returns the alpha-level velocity.
        """
        if(self.systemOrder == 1):
            alpha = self.ALPHA_M
        else:
            alpha = self.ALPHA_F
        return x_alpha(alpha,self.xdot(),self.xdot_old)
    
    def xddot_alpha(self):
        """
        Returns the alpha-level acceleration.  Invalid for first-order
        ODE systems.
        """
        return x_alpha(self.ALPHA_M,self.xddot(),self.xddot_old)

    def advance(self):
        """
        Overwrites the data from the previous time step with the
        data from the current time step.
        """
        # must make copies first, to avoid using updated values in
        # self.xdot(), etc., then assign self.xdot, etc., to re-assigned
        # copies
        x_old = Function(self.x.function_space())
        xdot_old = Function(self.x.function_space())
        x_old.assign(self.x)
        xdot_old.assign(self.xdot())
        if(self.systemOrder==2):
            xddot_old = Function(self.x.function_space())
            xddot_old.assign(self.xddot())
        self.x_old.assign(x_old)
        self.xdot_old.assign(xdot_old)
        if(self.systemOrder==2):
            self.xddot_old.assign(xddot_old)
        self.t += float(self.DELTA_T)

