import toast from 'react-hot-toast'

export const showSuccessToast = (message) => {
  toast.success(message, {
    position: 'top-right',
    duration: 3000,
  })
}

export const showErrorToast = (message) => {
  toast.error(message, {
    position: 'top-right',
    duration: 3000,
  })
}

export const showLoadingToast = (message) => {
  return toast.loading(message, {
    position: 'top-right',
  })
}

export const updateToast = (toastId, message, type = 'success') => {
  toast.dismiss(toastId)
  if (type === 'success') {
    toast.success(message)
  } else if (type === 'error') {
    toast.error(message)
  }
}
