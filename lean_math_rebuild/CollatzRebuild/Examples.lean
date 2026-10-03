import CollatzRebuild.Core
import CollatzRebuild.OneStepIdentity

set_option autoImplicit false

namespace CollatzRebuild

theorem route_75 : iter 14 75 = 1 := by native_decide
theorem route_23 : iter 15 23 = 1 := by native_decide
theorem route_27 : iter 111 27 = 1 := by native_decide
theorem route_3152 : iter 31 3152 = 1 := by native_decide

end CollatzRebuild
