import tensorflow as tf

from Model.PDE_Model import PBE

# PBE Equations and schemes 

class PBE_Std(PBE):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.PDE_in = Poisson(self,self.inputs,field='phi')
        if self.eq=='linear':
            self.PDE_out = Helmholtz(self,self.inputs,field='phi')
        elif self.eq=='nonlinear':
            self.PDE_out = Non_Linear(self,self.inputs,field='phi')

    def get_phi(self,X,flag,model,value='phi'):
        if flag=='molecule':
            phi = tf.reshape(model(X,flag)[:,0], (-1,1))
        elif flag=='solvent':
            phi = tf.reshape(model(X,flag)[:,1], (-1,1))
        elif flag=='interface':
            phi = model(X,flag)

        if value=='phi':
            return phi 

        if value == 'react':
            if flag != 'interface':
                phi_r = phi - self.G(*self.mesh.get_X(X))
            elif flag =='interface':
                G_val = self.G(*self.mesh.get_X(X))
                phi_r = tf.stack([tf.reshape(phi[:,0],(-1,1))-G_val,tf.reshape(phi[:,1],(-1,1))-G_val], axis=1)
        return phi_r

    def get_dphi(self,X,Nv,flag,model,value='phi'):
        x = self.mesh.get_X(X)
        nv = self.mesh.get_X(Nv)
        du_1 = self.directional_gradient(self.mesh,model,x,nv,'molecule',value='phi')
        du_2 = self.directional_gradient(self.mesh,model,x,nv,'solvent',value='phi')
        if value=='react':
            du_1 -= self.dG_n(*x,Nv)
            du_2 -= self.dG_n(*x,Nv)
        return du_1,du_2


class PBE_Reg_1(PBE):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.PDE_in = Laplace(self,self.inputs,field='react')
        if self.eq=='linear':
            self.PDE_out = Helmholtz(self,self.inputs,field='react')
        elif self.eq=='nonlinear':
            self.PDE_out = Non_Linear(self,self.inputs,field='react')

    def get_phi(self,X,flag,model,value='phi'):
        if flag=='molecule':
            phi_r = tf.reshape(model(X,flag)[:,0], (-1,1)) 
        elif flag=='solvent':
            phi_r = tf.reshape(model(X,flag)[:,1], (-1,1))
        elif flag=='interface':
            phi_r = model(X,flag)
        
        if value =='react':
            return phi_r
        
        if value == 'phi':
            if flag != 'interface':
                phi = phi_r + self.G(*self.mesh.get_X(X))
            elif flag =='interface':
                G_val = self.G(*self.mesh.get_X(X))
                phi = tf.stack([tf.reshape(phi_r[:,0],(-1,1))+G_val,tf.reshape(phi_r[:,1],(-1,1))+G_val], axis=1)
        return phi 

    def get_dphi(self,X,Nv,flag,model,value='phi'):
        x = self.mesh.get_X(X)
        nv = self.mesh.get_X(Nv)
        du_1 = self.directional_gradient(self.mesh,model,x,nv,'molecule',value='react')
        du_2 = self.directional_gradient(self.mesh,model,x,nv,'solvent',value='react')
        if value=='phi':
            du_1 += self.dG_n(*x,Nv)
            du_2 += self.dG_n(*x,Nv)
        return du_1,du_2


class PBE_Reg_2(PBE):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.PDE_in = Laplace(self,self.inputs,field='react')
        if self.eq=='linear':
            self.PDE_out = Helmholtz(self,self.inputs,field='phi')
        elif self.eq=='nonlinear':
            self.PDE_out = Non_Linear(self,self.inputs,field='phi')

    def get_phi(self,X,flag,model,value='phi'):
        if flag=='molecule':
            phi_r = tf.reshape(model(X,flag)[:,0], (-1,1)) 
        elif flag=='solvent':
            phi_r = tf.reshape(model(X,flag)[:,1], (-1,1)) - self.G(*self.mesh.get_X(X))
        elif flag=='interface':
            phi_t = model(X,flag)
            G_val = self.G(*self.mesh.get_X(X))
            phi_r = tf.stack([tf.reshape(phi_t[:,0],(-1,1)),tf.reshape(phi_t[:,1],(-1,1))-G_val], axis=1)

        if value =='react':
            return phi_r
        
        if value == 'phi':
            if flag != 'interface':
                phi = phi_r + self.G(*self.mesh.get_X(X))
            elif flag =='interface':
                G_val = self.G(*self.mesh.get_X(X))
                phi = tf.stack([tf.reshape(phi_r[:,0],(-1,1))+G_val,tf.reshape(phi_r[:,1],(-1,1))+G_val], axis=1)
        return phi 

    def get_dphi(self,X,Nv,flag,model,value='phi'):
        x = self.mesh.get_X(X)
        nv = self.mesh.get_X(Nv)
        du_1 = self.directional_gradient(self.mesh,model,x,nv,'molecule',value='react')
        du_2 = self.directional_gradient(self.mesh,model,x,nv,'solvent',value='phi')
        if value=='phi':
            du_1 += self.dG_n(*x,Nv)
        elif value =='react':
            du_2 -= self.dG_n(*x,Nv)
        return du_1,du_2
    

# Residuals

class Laplace():

    def __init__(self, PBE, inputs,field):
        
        self.PBE = PBE
        self.field = field
        for key, value in inputs.items():
            setattr(self, key, value)
        self.epsilon = self.epsilon_1
        super().__init__()

    def residual_loss(self,mesh,model,X,SU,flag):
        x,y,z = X
        r = self.PBE.laplacian(mesh,model,X,flag,value=self.field)     
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r


class Poisson():

    def __init__(self, PBE, inputs, field):
        
        self.PBE = PBE
        self.field = field
        for key, value in inputs.items():
            setattr(self, key, value)
        self.epsilon = self.epsilon_1
        super().__init__()

    def residual_loss(self,mesh,model,X,SU,flag):
        x,y,z = X
        r = self.PBE.laplacian(mesh,model,X,flag, value=self.field) - SU       
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r


class Helmholtz():

    def __init__(self, PBE, inputs, field):

        self.PBE = PBE
        self.field = field
        for key, value in inputs.items():
            setattr(self, key, value)
        self.epsilon = self.epsilon_2
        super().__init__()

    def residual_loss(self,mesh,model,X,SU,flag):
        x,y,z = X
        R = mesh.stack_X(x,y,z)
        u = self.PBE.get_phi(R,flag,model,value=self.field)
        r = self.PBE.laplacian(mesh,model,X,flag,value=self.field) - self.kappa**2*u      
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r  


class Non_Linear():

    def __init__(self, PBE, inputs, field):

        self.PBE = PBE
        self.field = field
        for key, value in inputs.items():
            setattr(self, key, value)
        self.epsilon = self.epsilon_2
        super().__init__()

    def residual_loss(self,mesh,model,X,SU,flag):
        x,y,z = X
        R = mesh.stack_X(x,y,z)
        u = self.PBE.get_phi(R,flag,model,value=self.field)
        r = self.PBE.laplacian(mesh,model,X,flag,value=self.field) - self.kappa**2*tf.math.sinh(u)     
        Loss_r = tf.reduce_mean(tf.square(r))
        return Loss_r
    