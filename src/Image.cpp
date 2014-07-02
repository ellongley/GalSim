/* -*- c++ -*-
 * Copyright (c) 2012-2014 by the GalSim developers team on GitHub
 * https://github.com/GalSim-developers
 *
 * This file is part of GalSim: The modular galaxy image simulation toolkit.
 * https://github.com/GalSim-developers/GalSim
 *
 * GalSim is free software: redistribution and use in source and binary forms,
 * with or without modification, are permitted provided that the following
 * conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions, and the disclaimer given in the accompanying LICENSE
 *    file.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions, and the disclaimer given in the documentation
 *    and/or other materials provided with the distribution.
 */

#include <sstream>

#include "Image.h"
#include "ImageArith.h"
#include "FFT.h"

namespace galsim {

/////////////////////////////////////////////////////////////////////
//// Constructor for out-of-bounds that has coordinate info
///////////////////////////////////////////////////////////////////////


std::string MakeErrorMessage(
    const std::string& m, const int min, const int max, const int tried)
{
    // See discussion in Std.h about this initial value.
    std::ostringstream oss(" ");
    oss << "Attempt to access "<<m<<" number "<<tried
        << ", range is "<<min<<" to "<<max;
    return oss.str();
}
ImageBoundsError::ImageBoundsError(
    const std::string& m, const int min, const int max, const int tried) :
    ImageError(MakeErrorMessage(m,min,max,tried)) 
{}

std::string MakeErrorMessage(const int x, const int y, const Bounds<int> b) 
{
    std::ostringstream oss(" ");
    bool found=false;
    if (x<b.getXMin() || x>b.getXMax()) {
        oss << "Attempt to access column number "<<x
            << ", range is "<<b.getXMin()<<" to "<<b.getXMax();
        found = true;
    }
    if (y<b.getYMin() || y>b.getYMax()) {
        if (found) oss << " and ";
        oss << "Attempt to access row number "<<y
            << ", range is "<<b.getYMin()<<" to "<<b.getYMax();
        found = true;
    } 
    if (!found) return "Cannot find bounds violation ???";
    else return oss.str();
}
ImageBoundsError::ImageBoundsError(const int x, const int y, const Bounds<int> b) :
    ImageError(MakeErrorMessage(x,y,b)) 
{}

/////////////////////////////////////////////////////////////////////
//// Constructor (and related helpers) for the various Image classes
///////////////////////////////////////////////////////////////////////

namespace {

template <typename T>
class ArrayDeleter {
public:
    void operator()(T * p) const { delete [] p; }
};

} // anonymous

template <typename T>
BaseImage<T>::BaseImage(const Bounds<int>& b) :
    AssignableToImage<T>(b), _owner(), _data(0), _nElements(0), _stride(0)
{
    if (this->_bounds.isDefined()) allocateMem();
    // Else _data is left as 0, stride = 0.
}

template <typename T>
void BaseImage<T>::allocateMem()
{
    // Note: this version always does the memory (re-)allocation. 
    // So the various functions that call this should do their (different) checks 
    // for whether this is necessary.
    _stride = this->_bounds.getXMax() - this->_bounds.getXMin() + 1;

    _nElements = _stride * (this->_bounds.getYMax() - this->_bounds.getYMin() + 1);
    if (_stride <= 0 || _nElements <= 0) {
        FormatAndThrow<ImageError>() << 
            "Attempt to create an Image with defined but invalid Bounds ("<<this->_bounds<<")";
    }

    // The ArrayDeleter is because we use "new T[]" rather than an normal new.
    // Without ArrayDeleter, shared_ptr would just use a regular delete, rather
    // than the required "delete []".
    _owner.reset(new T[_nElements], ArrayDeleter<T>());
    _data = _owner.get();
}

template <typename T>
ImageAlloc<T>::ImageAlloc(int ncol, int nrow, T init_value) :
    BaseImage<T>(Bounds<int>(1,ncol,1,nrow)) 
{
    if (ncol <= 0 || nrow <= 0) {
        std::ostringstream oss(" ");
        if (ncol <= 0) {
            if (nrow <= 0) {
                oss << "Attempt to create an Image with non-positive ncol ("<<
                    ncol<<") and nrow ("<<nrow<<")";
            } else {
                oss << "Attempt to create an Image with non-positive ncol ("<<
                    ncol<<")";
            }
        } else {
            oss << "Attempt to create an Image with non-positive nrow ("<<
                nrow<<")";
        }
        throw ImageError(oss.str());
    }
    fill(init_value);
}

template <typename T>
ImageAlloc<T>::ImageAlloc(const Bounds<int>& bounds, const T init_value) :
    BaseImage<T>(bounds)
{
    fill(init_value);
}

template <typename T>
void ImageAlloc<T>::resize(const Bounds<int>& new_bounds) 
{
    if (!new_bounds.isDefined()) {
        // Then this is really a deallocation.  Clear out the existing memory.
        this->_bounds = new_bounds;
        this->_owner.reset();
        this->_data = 0;
        this->_nElements = 0;
        this->_stride = 0;
    } else if (this->_bounds.isDefined() &&
               new_bounds.area() <= this->_nElements && 
               this->_owner.unique()) {
        // Then safe to keep existing memory allocation.
        // Just redefine the bounds and stride.
        this->_bounds = new_bounds;
        this->_stride = new_bounds.getXMax() - new_bounds.getXMin() + 1;
    } else {
        // Then we want to do the reallocation.
        this->_bounds = new_bounds;
        this->allocateMem();
    }
}


/////////////////////////////////////////////////////////////////////
//// Access methods
///////////////////////////////////////////////////////////////////////

template <typename T>
const T& BaseImage<T>::at(const int xpos, const int ypos) const
{
    if (!_data) throw ImageError("Attempt to access values of an undefined image");
    if (!this->_bounds.includes(xpos, ypos)) throw ImageBoundsError(xpos, ypos, this->_bounds);
    return _data[addressPixel(xpos, ypos)];
}

template <typename T>
T& ImageView<T>::at(const int xpos, const int ypos) const
{
    if (!this->_data) throw ImageError("Attempt to access values of an undefined image");
    if (!this->_bounds.includes(xpos, ypos)) throw ImageBoundsError(xpos, ypos, this->_bounds);
    return this->_data[this->addressPixel(xpos, ypos)];
}

template <typename T>
T& ImageAlloc<T>::at(const int xpos, const int ypos)
{
    if (!this->_data) throw ImageError("Attempt to access values of an undefined image");
    if (!this->_bounds.includes(xpos, ypos)) throw ImageBoundsError(xpos, ypos, this->_bounds);
    return this->_data[this->addressPixel(xpos, ypos)];
}

template <typename T>
const T& ImageAlloc<T>::at(const int xpos, const int ypos) const
{
    if (!this->_data) throw ImageError("Attempt to access values of an undefined image");
    if (!this->_bounds.includes(xpos, ypos)) throw ImageBoundsError(xpos, ypos, this->_bounds);
    return this->_data[this->addressPixel(xpos, ypos)];
}

template <typename T>
ConstImageView<T> BaseImage<T>::subImage(const Bounds<int>& bounds) const 
{
    if (!_data) throw ImageError("Attempt to make subImage of an undefined image");
    if (!this->_bounds.includes(bounds)) {
        FormatAndThrow<ImageError>() << 
            "Subimage bounds (" << bounds << ") are outside original image bounds (" << 
            this->_bounds << ")";
    }
    T* newdata = _data
        + (bounds.getYMin() - this->_bounds.getYMin()) * _stride
        + (bounds.getXMin() - this->_bounds.getXMin());
    return ConstImageView<T>(newdata,_owner,_stride,bounds);
}

template <typename T>
ImageAlloc<T> BaseImage<T>::applyCD(ConstImageView<double> aL, ConstImageView<double> aR, 
                                    ConstImageView<double> aB, ConstImageView<double> aT,
                                    const int dmax) const
{
    // Perform sanity check
    if(dmax < 0) throw ImageError("Attempt to apply CD model with invalid extent");
    // Get the array dimension and perform other checks
    const int arraydim = 1 + aL.getXMax() - aL.getXMin();
    if (arraydim != (2 * dmax + 1) * (2 * dmax + 1)) throw ImageError(
        "Dimensions of input image do not match specified dmax");
    if (1 + aR.getXMax() - aR.getXMin() != arraydim ||
        1 + aB.getXMax() - aB.getXMin() != arraydim ||
        1 + aT.getXMax() - aT.getXMin() != arraydim)
        throw ImageError("All input aL, aR, aB, aT Images must be the same dimensions");
    
    ImageAlloc<T> output(getXMax()-getXMin()+1,getYMax()-getYMin()+1);  
    // working version of image, which we later return
    
    for(int x=getXMin(); x<=getXMax(); x++){

        for(int y=getYMin(); y<=getYMax(); y++){

            double f = at(x, y);
	    
	    if(x<getXMin()+dmax || x>getXMax()-dmax || y<getYMin()+dmax || y>getYMax()-dmax) // outer pixel would not be flux conserving + require fencepost checks
	    {
	      output.setValue(x, y, f);
	      continue;
	    }
	    
            double    fT = (f + at(x, y + 1)) / 2.;
            double    fB = (f + at(x, y - 1)) / 2.;
            double    fR = (f + at(x + 1, y)) / 2.;
            double    fL = (f + at(x - 1, y)) / 2.;

            // for each surrounding pixel do
            int matrixindex = 0; // for iterating over the aL, aR, aB, aT images in 1d
            //std::cout << "### in " << x << " " << y << std::endl;
            for(int iy=-dmax; iy<=dmax; iy++){

                for(int ix=-dmax; ix<=dmax; ix++){

                    double qkl = at(x + ix, y + iy);
                    f += qkl * fT * aT.at(aT.getXMin() + matrixindex, aT.getYMin());
                    f += qkl * fB * aB.at(aB.getXMin() + matrixindex, aB.getYMin());
                    f += qkl * fL * aL.at(aL.getXMin() + matrixindex, aL.getYMin());
		    //if(fL>0)
		    //  std::cout << ix << " " << iy << " " << qkl << " * " << fL << " * " << aL.at(aL.getXMin() + matrixindex, aL.getYMin()) << std::endl;
                    f += qkl * fR * aR.at(aR.getXMin() + matrixindex, aR.getYMin());
                    matrixindex++;

                }

            }
            output.setValue(x, y, f);
        }
    }
    return output;
}

template <typename T>
ImageView<T> ImageView<T>::subImage(const Bounds<int>& bounds) const 
{
    if (!this->_data) throw ImageError("Attempt to make subImage of an undefined image");
    if (!this->_bounds.includes(bounds)) {
        FormatAndThrow<ImageError>() << 
            "Subimage bounds (" << bounds << ") are outside original image bounds (" << 
            this->_bounds << ")";
    }
    T* newdata = this->_data
        + (bounds.getYMin() - this->_bounds.getYMin()) * this->_stride
        + (bounds.getXMin() - this->_bounds.getXMin());
    return ImageView<T>(newdata,this->_owner,this->_stride,bounds);
}

namespace {

template <typename T>
class ConstReturn 
{
public: 
    ConstReturn(const T v): val(v) {}
    T operator()(const T ) const { return val; }
private:
    T val;
};

template <typename T>
class ReturnInverse
{
public: 
    double operator()(const T val) const { return val==T(0) ? 0. : 1./double(val); }
};

template <typename T>
class ReturnSecond 
{
public:
    T operator()(T, T v) const { return v; }
};

} // anonymous

template <typename T>
void ImageView<T>::fill(T x) const 
{
    transform_pixel(*this, ConstReturn<T>(x));
}

template <typename T>
void ImageView<T>::invertSelf() const 
{
    transform_pixel(*this, ReturnInverse<T>());
}

template <typename T>
void ImageView<T>::copyFrom(const BaseImage<T>& rhs) const
{
    if (!this->_bounds.isSameShapeAs(rhs.getBounds()))
        throw ImageError("Attempt im1 = im2, but bounds not the same shape");
    transform_pixel(*this, rhs, ReturnSecond<T>());
}

// instantiate for expected types

template class BaseImage<double>;
template class BaseImage<float>;
template class BaseImage<int32_t>;
template class BaseImage<int16_t>;
template class ImageAlloc<double>;
template class ImageAlloc<float>;
template class ImageAlloc<int32_t>;
template class ImageAlloc<int16_t>;
template class ImageView<double>;
template class ImageView<float>;
template class ImageView<int32_t>;
template class ImageView<int16_t>;
template class ConstImageView<double>;
template class ConstImageView<float>;
template class ConstImageView<int32_t>;
template class ConstImageView<int16_t>;

} // namespace galsim

