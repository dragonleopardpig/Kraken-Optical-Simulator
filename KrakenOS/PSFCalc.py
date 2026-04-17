#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  9 07:54:16 2021

@author: joelherreravazquez & Antonio A.

GPU-accelerated PSF / MTF calculations.  Heavy array work (FFT, exp,
meshgrid) is dispatched through ``xp`` which resolves to CuPy when a GPU
is available and falls back to NumPy otherwise.
"""

import numpy as np
import matplotlib.pyplot as plt
from .MathShapesClass import *
from .gpu_backend import xp, to_cpu

from scipy.ndimage import rotate


###############################################################################


def psf4mtf(COEF, Focal, Diameter, Wave, pixels=600, PupilSample=4):
    """Compute the PSF from Zernike coefficients (for MTF calculation)."""
    N = pixels
    Q = PupilSample

    TamImag = int(N)
    r = (TamImag / (Q * 2.0))
    center = int((TamImag / 2.0))
    xy = xp.arange(0, TamImag)
    X, Y = xp.meshgrid(xy, xy)
    x = (X - center) / r
    y = (Y - center) / r
    R = xp.sqrt(x**2 + y**2)

    W = Wavefront_Zernike_Phase(x, y, COEF)
    W[R > 1] = 0.0

    T = xp.ones_like(W)
    T[R > 1] = 0.0

    U = T * xp.exp(-1j * 2 * xp.pi * W)

    F0 = xp.fft.fftshift(xp.fft.fft2(xp.fft.fftshift(U))) / xp.sum(T)
    I = xp.abs(F0)**2

    return to_cpu(I)

def calculate_mtf(COEF, Focal, Diameter, w, pixels=600, PupilSample=4):
    """Compute the MTF from the PSF."""
    psf_arr = psf4mtf(COEF, Focal, Diameter, w, pixels=pixels, PupilSample=PupilSample)
    psf_arr = xp.asarray(psf_arr)
    psf_arr = psf_arr / xp.sum(psf_arr)
    F0 = xp.fft.fft2(psf_arr)
    F0 = xp.fft.fftshift(F0)
    mtf = xp.abs(F0)
    mtf = mtf / xp.max(mtf)
    return to_cpu(mtf)

def plot_mtf(mtf, Diameter, w, freq_limit = 1100):
    """Plot tangential and sagittal MTF curves."""
    N = mtf.shape[0]

    freq_max = (Diameter / (w * 1e-3))
    freq = np.linspace(0, freq_max, N // 2)

    mtf_tangential = mtf[N // 2, N // 2:]
    mtf_sagittal = mtf[N // 2:, N // 2]

    plt.figure(figsize=(10, 6))
    plt.plot(freq/10, mtf_tangential[:len(freq)], label='Tangential MTF', color='blue')
    plt.plot(freq/10, mtf_sagittal[:len(freq)], label='Sagittal MTF', color='red')
    plt.xlabel('Spatial Frequency in cycles per mm')
    plt.ylabel('Modulus of the OTF')
    plt.title('Polychromatic Diffraction MTF')
    plt.grid(True)
    plt.legend()

    plt.xlim(0, freq_limit)
    plt.ylim(0, 1)
    plt.show()



#########################################################################333

def psf(COEF, Focal, Diameter, Wave, pixels=600, PupilSample=4,  plot=0, sqr=0):

    ''' Generando los polinomios de Zernike (Nomenclarura Noll)con:
                   zernike_expand de Jherrera
    '''
    L=38 # Numero de terminos para la expanción polinomial


    ########################################################################

    '''Utilizando un solo valor de la pupila (x,y) con
                  Wavefront_Zernike_Phase
    '''
    Zern_pol, z_pow = zernike_expand(len(COEF))

    # ####################################################################

    """
            Generando un mapa de pupila aberrado
    """

    # Número de Elementos en el arreglo
    N = pixels

    # Variable de Muestreo
    Q=PupilSample

    #Diámetro de la Apertura [m]
    D=Diameter/1000.0

    #Diámetro de la Obstrucción[m]
    Do = 0.5
    #Número F
    FocalD=Focal/1000.0
    #Longitud de Onda [m]
    wvl=Wave*1e-6 # Cambiando wave a metros

    TamImag = int(N)
    r = (TamImag / (Q*2.0))

    center = int((TamImag / 2.0))
    xy=xp.arange(0,TamImag)
    [X,Y]=xp.meshgrid(xy, xy)
    x = ((X - center) / r)
    y = ((Y - center) / r)
    R=xp.sqrt((x**2)+(y**2))

    W = Wavefront_Zernike_Phase(x, y, COEF)

    f=R>1
    W[f]=0.0

    T=xp.copy(W)
    f=R<=1
    T[f]=1.0
    #Area del Círculo
    a=xp.sum(xp.sum(T))

    #Función de Pupila
    ##############################################################
    #Mapa del Frente de Onda con Máscara [wvl rms]
    #Campo complejo
    U=T*xp.exp(-1j*2*xp.pi*W)

    #PSF-Fraunhofer
    ##############################################################
    #TF de la distribución de Amplitud en Pupila
    F0=xp.fft.fftshift(xp.fft.fft2(xp.fft.fftshift(U)))/a
    #Irradiancia en el Plano de Observación
    I=xp.abs(F0)**2

    #Vector de Muestras con Cero en el Centro
    ##############################################################
    #Vector de Muestras
    v=xp.arange(0,N)
    #Elemento central [bin]
    c=int(xp.floor(N/2.))
    #Corriendo el cero al centro
    vx=v-c
    vy=c-v

    #Coordenadas del Plano de la Apertura
    ##############################################################
    #Largo del Plano
    L=Q*D
    ##############################################################
    #Coordenadas del Plano de Imagen
    #Tamaño del paso en frecuencia [m^-1]
    f=1/L
    # Vector de Coordenadas fx y fy
    fx=f*vx
    fy=f*vy

    # Vector de Coordenadas x y y
    u=fx*wvl*FocalD
    v=fy*wvl*FocalD

    # Convert to CPU for extent calculation and plotting
    u = to_cpu(u)
    v = to_cpu(v)
    I = to_cpu(I)

    umx=u[N-1]*1e6
    umn=u[0]*1e6
    vmx=v[N-1]*1e6
    vmn=v[0]*1e6

    I = np.rot90(I)

    # Saturando la Imagen
    if plot !=0:
        plt.figure("PSF")
        if sqr == 0:
            plt.imshow(I,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF')

        if sqr == 1:
            II=np.sqrt(I/np.max(I))*255
            plt.imshow(II,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF ( note: sqrt(I) )')

        if sqr == 2:
            III = np.log(I)
            III = III-np.min(III)
            III = 255*III/np.max(III)

            plt.imshow(III,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF ( note: sqrt(I) )')

    return I




def PsfPlus(COEF, Focal, Diameter, Wave, pixels=600, PupilSample=4,  plot=0, sqr=0):

    ''' Generando los polinomios de Zernike (Nomenclarura Noll)con:
                   zernike_expand de Jherrera
    '''
    L=38 # Numero de terminos para la expanción polinomial


    ########################################################################

    '''Utilizando un solo valor de la pupila (x,y) con
                  Wavefront_Zernike_Phase
    '''
    Zern_pol, z_pow = zernike_expand(len(COEF))

    # ####################################################################

    """
            Generando un mapa de pupila aberrado
    """

    # Número de Elementos en el arreglo
    N = pixels

    # Variable de Muestreo
    Q = PupilSample

    #Diámetro de la Apertura [m]
    D = Diameter / 1000.0

    #Diámetro de la Obstrucción[m]
    Do = 0.5
    #Número F
    FocalD = Focal / 1000.0
    #Longitud de Onda [m]
    wvl = Wave*1e-6 # Cambiando wave a metros

    TamImag = int(N)
    r = (TamImag / (Q * 2.0))

    center = int((TamImag / 2.0))
    xy = xp.arange(0,TamImag)
    [X,Y] = xp.meshgrid(xy, xy)
    x = ((X - center) / r)
    y = ((Y - center) / r)
    R = xp.sqrt((x**2)+(y**2))

    W = Wavefront_Zernike_Phase(x, y, COEF)

    f = R>1
    W[f] = 0.0

    T = xp.copy(W)
    f = R <= 1
    T[f] = 1.0
    #Area del Círculo
    a = xp.sum(xp.sum(T))

    #Función de Pupila
    ##############################################################
    #Mapa del Frente de Onda con Máscara [wvl rms]

    #Campo complejo
    U = T * xp.exp( -1j * 2 * xp.pi * W )

    #PSF-Fraunhofer
    ##############################################################
    #TF de la distribución de Amplitud en Pupila
    F0 = xp.fft.fftshift(xp.fft.fft2(xp.fft.fftshift(U))) / a

    #Irradiancia en el Plano de Observación
    I=xp.abs(F0)**2

    #Vector de Muestras con Cero en el Centro
    ##############################################################
    #Vector de Muestras
    v=xp.arange(0,N)
    #Elemento central [bin]
    c=int(xp.floor(N/2.))
    #Corriendo el cero al centro
    vx=v-c
    vy=c-v

    #Coordenadas del Plano de la Apertura
    ##############################################################
    #Largo del Plano
    L=Q*D
    ##############################################################
    #Coordenadas del Plano de Imagen
    #Tamaño del paso en frecuencia [m^-1]
    f=1/L
    # Vector de Coordenadas fx y fy
    fx=f*vx
    fy=f*vy

    # Vector de Coordenadas x y y
    u=fx*wvl*FocalD
    v=fy*wvl*FocalD

    # Convert to CPU for extent calculation and plotting
    u = to_cpu(u)
    v = to_cpu(v)
    I = to_cpu(I)

    umx=u[N-1]*1e6
    umn=u[0]*1e6
    vmx=v[N-1]*1e6
    vmn=v[0]*1e6

    I = np.rot90(I)

    # Saturando la Imagen
    if plot !=0:
        plt.figure("PSF")
        if sqr == 0:
            plt.imshow(I,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF')

        if sqr == 1:
            II=np.sqrt(I/np.max(I))*255
            plt.imshow(II,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF ( note: sqrt(I) )')

        if sqr == 2:
            III = np.log(I)
            III = III-np.min(III)
            III = 255*III/np.max(III)

            plt.imshow(III,extent=[umn,umx,vmx,vmn], cmap= plt.cm.bone)
            plt.colorbar()
            plt.ylabel('V[μm]')
            plt.xlabel('U[μm]')
            plt.title('Fraunhofer Prop - PSF ( note: sqrt(I) )')

    return I, vmn*2
