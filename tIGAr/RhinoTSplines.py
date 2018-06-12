"""
The ``RhinoTSplines`` module
----------------------------
is a proof-of-concept implementation of generating ``tIGAr``-type extraction
data from the output of commercial CAD software.  In particular, it reads
data generated by the (now defunct) Rhino T-splines plugin.
"""

from tIGAr.common import *
#from tIGAr.BSplines import *

# important case of output from Rhino T-splines plugin: bi-variate cubic
# Bezier elements

# cubic Bernstein basis on -1 to 1 interval
def Bernstein_p3(u):
    """
    Because Rhino outputs element-by-element extraction data assuming a 
    Bezier basis on each element, we evaluate T-spline basis functions
    in terms of Bezier basis functions (even though we are extracting to
    Lagrange elements).  This function returns a list of the four cubic
    Bernstein polynomials on (-1,1) evaluated at parameter ``u`` in that
    interval.
    """
    # re-use B-spline machinery
    #knots = [-1.0,-1.0,-1.0,-1.0,1.0,1.0,1.0,1.0]
    #spline = BSpline1(3,knots)
    #return spline.basisFuncs(3,u)
    B = [0.0,0.0,0.0,0.0]
    x = 0.5*(1.0+u)
    B[0] = (1.0-x)**3
    B[1] = 3.0*x*((1.0-x)**2)
    B[2] = 3.0*(x**2)*(1.0-x)
    B[3] = x**3
    return B

def RhinoTSplineScalarBasisFuncs(xi,C):
    """
    Use the Berstein basis functions and a Rhino-format extraction operator
    ``C`` to evaluate T-spline basis functions at parameters ``xi`` in
    a Bezier element parameterized by (-1,1)^2.  

    Rhino's format:  ``C`` is a matrix in which each row specifies a 
    linear combination of Bezier shape functions.
    """
    u = xi[0]
    v = xi[1]
    M = Bernstein_p3(u)
    N = Bernstein_p3(v)
    Bern = []
    for j in range(0,4):
        for i in range(0,4):
            Bern += [M[i]*N[j],]
    tmpshl = []
    for aa in range(0,len(C)):
        tmpshlaa = 0.0
        for bb in range(0,16):
            tmpshlaa += C[aa][bb]*Bern[bb]
        tmpshl += [tmpshlaa,]
    return tmpshl

# Implementation: get everything covered by one coordinate chart,
# space out elements so that element i goes from 3.0*i to 3.0*i+2.0
# in x0 direction.  Thus, if we round down (x0/3.0 + EPS), it returns
# the element index, and we have u = x0 - 3.0*i - 1.0, v = x1 for
# eval-ing shape functions
class RhinoTSplineScalarBasis(AbstractScalarBasis):

    def __init__(self,fname,useRect=USE_RECT_ELEM_DEFAULT):
        """
        Generates an instance of ``RhinoTSplineScalarBasis`` from 
        element-by-element extraction data in the file ``fname``.  Can
        optionally choose whether or not to use rectangular elements for
        extraction by setting Boolean argument ``useRect``.
        """
        self.nvar = 2
        self.useRect = useRect
        # read in a T-spline patch from file fname
        # TODO: do this efficiently w/ numpy arrays instead of py lists
        f = open(fname,"r")
        fs = f.read()
        f.close()
        lines = fs.split('\n')
        self.ncp = int(lines[1].split()[1])
        self.nelBez = int(lines[2].split()[1])

        # Changed for true format
        #lineCounter = 4+self.ncp
        lineCounter = 3+self.ncp
        
        self.extractionOperators = []
        self.extractionNodes = []
        self.maxNshl = 0
        for i in range(0,self.nelBez):
            nshl = int(lines[lineCounter].split()[1])
            if(nshl > self.maxNshl):
                self.maxNshl = nshl
            nodeStrings = lines[lineCounter+1].split()
            nodes = []
            for ns in nodeStrings:
                nodes += [int(ns),]
            self.extractionNodes += [nodes,]
            C = []
            for j in range(0,nshl):
                coeffStrings = lines[lineCounter+2+j].split()
                coeffs = []
                for cs in coeffStrings:
                    coeffs += [float(cs),]
                C += [coeffs,]
            lineCounter += nshl+2
            self.extractionOperators += [C,]
            
        # TODO: read in BC info

    #def getParametricDimension(self):
    #    return self.nvar

    def getPrealloc(self):
        return self.maxNshl
    
    def useRectangularElements(self):
        return self.useRect

    def needsDG(self):
        return False
    
    def getNodesAndEvals(self,xi):
        elementIndex = int(xi[0]/3.0 + 0.1)
        u = xi[0] - 3.0*elementIndex - 1.0
        v = xi[1]
        C = self.extractionOperators[elementIndex]
        nodes = self.extractionNodes[elementIndex]
        evals = RhinoTSplineScalarBasisFuncs([u,v],C)
        nodesAndEvals = []
        for i in range(0,len(nodes)):
            nodesAndEvals +=[[nodes[i],evals[i]],]
        return nodesAndEvals

    MESH_FILE_NAME = "mesh.xml"
            
    def generateMesh(self):
        # brute force approach: write out an xml file on mpi task zero, then
        # read it back in in parallel
        #
        # TODO: should figure out how to use DOLFIN MeshEditor for this
        if(mpirank == 0):
            fs = '<?xml version="1.0" encoding="UTF-8"?>' + "\n"
            fs += '<dolfin xmlns:dolfin="http://www.fenics.org/dolfin/">'+"\n"
            if(self.useRect):
                fs += '<mesh celltype="quadrilateral" dim="2">' + "\n"
                nverts = 4*self.nelBez
                nel = self.nelBez
                fs += '<vertices size="'+str(nverts)+'">' + "\n"
                vertCounter = 0
                for i in range(0,self.nelBez):
                    x0 = repr(3.0*i)
                    x1 = repr(3.0*i+2.0)
                    y0 = repr(-1.0)
                    y1 = repr(1.0)
                    fs += '<vertex index="'+str(vertCounter)\
                          +'" x="'+x0+'" y="'+y0+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+1)\
                          +'" x="'+x1+'" y="'+y0+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+2)\
                          +'" x="'+x0+'" y="'+y1+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+3)\
                          +'" x="'+x1+'" y="'+y1+'"/>' + "\n"
                    vertCounter += 4
                fs += '</vertices>' + "\n"
                fs += '<cells size="'+str(nel)+'">' + "\n"
                elCounter = 0
                for i in range(0,self.nelBez):
                    v0 = str(i*4+0)
                    v1 = str(i*4+1)
                    v2 = str(i*4+2)
                    v3 = str(i*4+3)
                    fs += '<quadrilateral index="'+str(elCounter)\
                          +'" v0="'+v0+'" v1="'+v1\
                          +'" v2="'+v2+'" v3="'+v3+'"/>'\
                          + "\n"
                    elCounter += 1
                fs += '</cells></mesh></dolfin>'
            else:
                fs += '<mesh celltype="triangle" dim="2">' + "\n"
                nverts = 4*self.nelBez
                nel = 2*self.nelBez
                fs += '<vertices size="'+str(nverts)+'">' + "\n"
                vertCounter = 0
                for i in range(0,self.nelBez):
                    x0 = repr(3.0*i)
                    x1 = repr(3.0*i+2.0)
                    y0 = repr(-1.0)
                    y1 = repr(1.0)
                    fs += '<vertex index="'+str(vertCounter)\
                          +'" x="'+x0+'" y="'+y0+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+1)\
                          +'" x="'+x1+'" y="'+y0+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+2)\
                          +'" x="'+x0+'" y="'+y1+'"/>' + "\n"
                    fs += '<vertex index="'+str(vertCounter+3)\
                          +'" x="'+x1+'" y="'+y1+'"/>' + "\n"
                    vertCounter += 4
                fs += '</vertices>' + "\n"
                fs += '<cells size="'+str(nel)+'">' + "\n"
                elCounter = 0
                for i in range(0,self.nelBez):
                    v0 = str(i*4+0)
                    v1 = str(i*4+1)
                    v2 = str(i*4+3)
                    fs += '<triangle index="'+str(elCounter)\
                          +'" v0="'+v0+'" v1="'+v1+'" v2="'+v2+'"/>'\
                          + "\n"
                    v0 = str(i*4+0)
                    v1 = str(i*4+3)
                    v2 = str(i*4+2)
                    fs += '<triangle index="'+str(elCounter+1)\
                          +'" v0="'+v0+'" v1="'+v1+'" v2="'+v2+'"/>'\
                          + "\n"
                    elCounter += 2
                fs += '</cells></mesh></dolfin>'
            f = open(self.MESH_FILE_NAME,'w')
            f.write(fs)
            f.close()

        MPI.barrier(mycomm)
            
        mesh = Mesh(self.MESH_FILE_NAME)

        return mesh

    def getNcp(self):
        return self.ncp

    def getDegree(self):
        if(self.useRect):
            return 3
        else:
            return 6

class RhinoTSplineControlMesh(AbstractControlMesh):

    """
    This class uses a ``RhinoTSplineScalarBasis`` and control point data
    from Rhino to represent a mapping from parametric to physical space.
    """
    
    def __init__(self,fname,useRect=USE_RECT_ELEM_DEFAULT):
        """
        Initialize a control mesh by reading extraction data and control
        points from a Rhino T-spline file named ``fname``.  Can
        optionally choose whether or not to use rectangular elements for
        extraction by setting Boolean argument ``useRect``.
        """
        self.scalarSpline = RhinoTSplineScalarBasis(fname,useRect)
        self.nsd = 3
        # read in control net from fname
        f = open(fname,"r")
        fs = f.read()
        f.close()

        lines = fs.split("\n")
        nnode = self.scalarSpline.getNcp()
        self.bnet = zeros((nnode,self.nsd+1))
        for i in range(0,nnode):
            # for manually-modified format
            #ii = i + 4
            # for files directly from rhino
            ii = i + 3
            coordStrs = lines[ii].split()
            for j in range(0,self.nsd+1):
                self.bnet[i,j] = float(coordStrs[j+1])
        # homogenize
        for i in range(0,nnode):
            for j in range(0,self.nsd):
                self.bnet[i,j] *= self.bnet[i,self.nsd]

    def getHomogeneousCoordinate(self,node,direction):
        return self.bnet[node,direction]
                
    def getScalarSpline(self):
        return self.scalarSpline

    def getNsd(self):
        return self.nsd
