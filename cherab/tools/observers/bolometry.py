
# Copyright 2014-2017 United Kingdom Atomic Energy Authority
#
# Licensed under the EUPL, Version 1.1 or – as soon they will be approved by the
# European Commission - subsequent versions of the EUPL (the "Licence");
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at:
#
# https://joinup.ec.europa.eu/software/page/eupl5
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the Licence is distributed on an "AS IS" basis, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.
#
# See the Licence for the specific language governing permissions and limitations
# under the Licence.

from raysect.core import Node, AffineMatrix3D, translate, rotate_basis, Point3D, Vector3D
from raysect.optical import Spectrum
from raysect.optical.observer import PowerPipeline0D, SightLine, TargetedPixel


class BolometerCamera(Node):
    """
    A group of bolometer sight-lines under a single scene-graph node.

    A scene-graph object regrouping a series of 'BolometerFoil'
    observers as a scene-graph parent. Allows combined observation and display
    control simultaneously.
    """

    def __init__(self, parent=None, transform=None, name=''):
        super().__init__(parent=parent, transform=transform, name=name)

        self._sight_lines = []

    def __getitem__(self, item):

        if isinstance(item, int):
            try:
                return self._sight_lines[item]
            except IndexError:
                raise IndexError("Sight-line number {} not available in this LineOfSightGroup.".format(item))
        elif isinstance(item, str):
            for sight_line in self._sight_lines:
                if sight_line.name == item:
                    return sight_line
            else:
                raise ValueError("Sightline '{}' was not found in this LineOfSightGroup.".format(item))
        else:
            raise TypeError("LineOfSightGroup key must be of type int or str.")

    @property
    def sight_lines(self):
        return self._sight_lines

    @sight_lines.setter
    def sight_lines(self, value):

        if not isinstance(value, list):
            raise TypeError("The sightlines attribute of LineOfSightGroup must be a list of SpectroscopicSightLines.")

        for sight_line in value:
            if not isinstance(sight_line, SpectroscopicSightLine):
                raise TypeError("The sightlines attribute of LineOfSightGroup must be a list of "
                                "SpectroscopicSightLines. Value {} is not a SpectroscopicSightLine.".format(sight_line))

        # Prevent external changes being made to this list
        value = value.copy()
        for sight_line in value:
            sight_line.parent = self

        self._sight_lines = value

    def add_sight_line(self, sight_line):

        if not isinstance(sight_line, SpectroscopicSightLine):
            raise TypeError("The sightline argument must be of type SpectroscopicSightLine.")

        sight_line.parent = self
        self._sight_lines.append(sight_line)

    def observe(self):
        for sight_line in self._sight_lines:
            sight_line.observe()

    def plot_spectra(self, unit='J', ymax=None):

        for sight_line in self.sight_lines:
            sight_line.plot_spectra(unit=unit, extras=False)

        if ymax is not None:
            plt.ylim(ymax=ymax)

        plt.title(self.name)
        plt.xlabel('wavelength (nm)')
        plt.ylabel('radiance ({}/s/m^2/str/nm)'.format(unit))
        plt.legend()


class BolometerSlit(Node):

    def __init__(self, centre_point, basis_x, dx, basis_y, dy, dz=0.001, parent=None, transform=None, name=''):

        self.name = name
        self.centre_point = centre_point
        self.basis_x = basis_x
        self.dx = dx
        self.basis_y = basis_y
        self.dy = dy
        self.dz = dz


class BolometerFoil:
    """
    A rectangular bolometer detector.

    Can be configured to sample a single ray or fan of rays oriented along the
    observer's z axis in world space.
    """

    def __init__(self, name, centre_point, basis_vectors, dx, dy, slit, ray_type="Targeted", parent=None):

        self._centre_point = Point3D(0, 0, 0)
        self._normal_vec = Vector3D(1, 0, 0)
        self._basis_x = Vector3D(0, 1, 0)
        self._transform = AffineMatrix3D()
        self._spectral_pipeline = PowerPipeline0D(accumulate=False)

        self.name = name

        if ray_type == "Sightline":
            self._observer = SightLine(pipelines=[self._spectral_pipeline], pixel_samples=1, parent=parent, name=name)
        elif ray_type == "Targeted":
            self._observer = TargetedPixel(parent=parent, target=slit, pipelines=[self._spectral_pipeline], name=name)
        else:
            raise ValueError("ray_type argument for BolometerFoil must be in ['Sightline', 'Targeted'].")

        if not isinstance(centre_point, Point3D):
            raise TypeError("centre_point argument for BolometerFoil must be of type Point3D.")
        self.centre_point = centre_point

        self.basis_vectors = basis_vectors

        if not isinstance(dx, float):
            raise TypeError("dx argument for BolometerFoil must be of type float.")
        if not dx > 0:
            raise ValueError("dx argument for BolometerFoil must be greater than zero.")
        self.dx = dx

        if not isinstance(dy, float):
            raise TypeError("dy argument for BolometerFoil must be of type float.")
        if not dy > 0:
            raise ValueError("dy argument for BolometerFoil must be greater than zero.")
        self.dy = dy

        if not isinstance(slit, BolometerSlit):
            raise TypeError("slit argument for BolometerFoil must be of type BolometerSlit.")
        self.slit = slit

    @property
    def centre_point(self):
        return self._centre_point

    @centre_point.setter
    def centre_point(self, value):
        self._centre_point = value
        self._observer.transform = translate(value.x, value.y, value.z) * rotate_basis(self._normal_vec, self._basis_x)

    @property
    def basis_vectors(self):
        return self._normal_vec, self._basis_x

    @basis_vectors.setter
    def basis_vectors(self, value):

        if not isinstance(value, tuple):
            raise TypeError("basis_vectors property of BolometerFoil must be a tuple of Vector3Ds.")

        normal_vec = value[0]
        if not isinstance(normal_vec, Vector3D):
            raise TypeError("basis_vectors property of BolometerFoil must be a tuple of Vector3Ds.")
        basis_x = value[1]
        if not isinstance(basis_x, Vector3D):
            raise TypeError("basis_vectors property of BolometerFoil must be a tuple of Vector3Ds.")

        if not normal_vec.dot(basis_x) == 0:
            raise ValueError("The normal and x basis vectors must be orthogonal to define a basis set.")

        self._normal_vec = normal_vec
        self._basis_x = basis_x
        translation = translate(self._centre_point.x, self._centre_point.y, self._centre_point.z)
        rotation = rotate_basis(normal_vec, basis_x)
        self._observer.transform = translation * rotation

    @property
    def min_wavelength(self):
        return self._observer.min_wavelength

    @min_wavelength.setter
    def min_wavelength(self, value):
        self._observer.min_wavelength = value

    @property
    def max_wavelength(self):
        return self._observer.max_wavelength

    @max_wavelength.setter
    def max_wavelength(self, value):
        self._observer.max_wavelength = value

    @property
    def spectral_bins(self):
        return self._observer.spectral_bins

    @spectral_bins.setter
    def spectral_bins(self, value):
        self._observer.spectral_bins = value

    @property
    def observed_spectrum(self):
        # TODO - throw exception if no observed spectrum
        pipeline = self._spectral_pipeline
        spectrum = Spectrum(pipeline.min_wavelength, pipeline.max_wavelength, pipeline.bins)
        spectrum.samples = pipeline.samples.mean
        return spectrum

    def observe(self):
        """
        Ask this sight-line to observe its world.
        """

        self._observer.observe()

    def plot_spectra(self, unit='J', ymax=None, extras=True):
        """
        Plot the observed spectrum.
        """

        if unit == 'J':
            # Spectrum objects are already in J/s/m2/str/nm
            spectrum = self.observed_spectrum
        elif unit == 'ph':
            # turn the samples into ph/s/m2/str/nm
            spectrum = self.observed_spectrum.new_spectrum()
            spectrum.samples = self.observed_spectrum.to_photons()
        else:
            raise ValueError("unit must be 'J' or 'ph'.")

        plt.plot(spectrum.wavelengths, spectrum.samples)

        if extras:
            if ymax is not None:
                plt.ylim(ymax=ymax)
            plt.title(self.name)
            plt.xlabel('wavelength (nm)')
            plt.ylabel('radiance ({}/s/m^2/str/nm)'.format(unit))


