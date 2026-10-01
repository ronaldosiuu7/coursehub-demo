students = [
    {"id": "22000001", "name": "Nguyen Minh Anh", "major": "KHDL"},
    {"id": "22000002", "name": "Tran Duc Long", "major": "KHDL"},
]

courses = [
    {
        "code": "INT2204",
        "name": "Co so du lieu Web va he thong thong tin",
        "capacity": 3,
        "enrolled": 2,
    },
    {
        "code": "INT2205",
        "name": "Khai pha du lieu",
        "capacity": 2,
        "enrolled": 2,
    },
]

enrollments = [
    {"student_id": "22000001", "course_code": "INT2204"}
]



def find_course(course_code):
    for course in courses:
        if course["code"] == course_code:
            return course
    return None

def find_student(student_id):
    for student in students:
        if student["id"] == student_id:
            return student
    return None


# ham enroll_student
def enroll_student(student_id, course_code):
    """
    Kiểm tra các quy tắc nghiệp vụ:
    - Sinh viên phải tồn tại
    - Học phần phải tồn tại
    - Lớp học phần còn chỗ trống
    - Sinh viên chưa đăng ký học phần này trước đó
    """
    # 1. Kiểm tra sinh viên tồn tại
    student = find_student(student_id)
    if student is None:
        return False, "Sinh vien khong ton tai"

    # 2. Kiểm tra học phần tồn tại
    course = find_course(course_code)
    if course is None:
        return False, "Hoc phan khong ton tai"

    # 3. Kiểm tra lớp còn chỗ
    if course["enrolled"] >= course["capacity"]:
        return False, "Lop da du so luong"

    # 4. Kiểm tra đăng ký trùng
    is_duplicated = any(
        item["student_id"] == student_id and item["course_code"] == course_code
        for item in enrollments
    )
    if is_duplicated:
        return False, "Sinh vien da dang ky hoc phan nay"

    
    enrollments.append({"student_id": student_id, "course_code": course_code})
    course["enrolled"] += 1
    return True, "Dang ky thanh cong"


# 5 TÌNH HUỐNG THỬ NGHIỆM
if __name__ == "__main__":
    print("=== CHẠY CÁC TÌNH HUỐNG KIỂM THỬ ===")
     
    # Mã sinh viên không tồn tại
    res1, msg1 = enroll_student("99999999", "INT2204")
    print(f"Test 1 (SV không tồn tại): {res1} -> {msg1}")

    #Mã học phần không tồn tại
    res2, msg2 = enroll_student("22000002", "INT9999")
    print(f"Test 2 (Học phần không tồn tại): {res2} -> {msg2}")

    # Lớp đã đầy chỗ (INT2205 có capacity=2, enrolled=2)
    res3, msg3 = enroll_student("22000002", "INT2205")
    print(f"Test 3 (Lớp đầy): {res3} -> {msg3}")

    # Đăng ký trùng (22000001 đã đăng ký INT2204)
    res4, msg4 = enroll_student("22000001", "INT2204")
    print(f"Test 4 (Đăng ký trùng): {res4} -> {msg4}")

    #Đăng ký thành công (22000002 đăng ký INT2204 còn 1 chỗ)
    res5, msg5 = enroll_student("22000002", "INT2204")
    print(f"Test 5 (Đăng ký thành công): {res5} -> {msg5}")

    # Kiểm tra trạng thái dữ liệu sau khi đăng ký thành công
    course_updated = find_course("INT2204")
    print(f"\nSố lượng sau cập nhật của INT2204: {course_updated['enrolled']}/{course_updated['capacity']}")
    print(f"Danh sách enrollments hiện tại: {enrollments}")