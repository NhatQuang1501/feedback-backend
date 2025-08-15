from django.db.models import Q, F, Func, TextField
from django.db.models.functions import Lower


def get_multi_values(request, key):
    """
    Thu thập các query params có nhiều giá trị và chuẩn hóa CSV.
    Hỗ trợ: key=a&key=b, key[]=a&key[]=b, và key=a,b
    Trả về danh sách các chuỗi đã được cắt khoảng trắng và loại bỏ chuỗi rỗng.
    """
    raw_values = []
    raw_values.extend(request.query_params.getlist(key))
    raw_values.extend(request.query_params.getlist(f"{key}[]"))

    single = request.query_params.get(key)
    if single:
        raw_values.append(single)

    values = []
    for item in raw_values:
        if not isinstance(item, str):
            continue
        for part in item.split(","):
            part_clean = part.strip()
            if part_clean:
                values.append(part_clean)
    return values


def apply_feedback_filters(queryset, status_values, type_values, priority_values):
    """Áp dụng bộ lọc trạng thái/loại/độ ưu tiên khi có giá trị."""
    if status_values:
        queryset = queryset.filter(status__name__in=[v for v in status_values if v])
    if type_values:
        queryset = queryset.filter(type__name__in=[v for v in type_values if v])
    if priority_values:
        queryset = queryset.filter(priority__name__in=[v for v in priority_values if v])
    return queryset


def apply_keyword_search(queryset, keyword):
    """Search behavior:
    - ASCII (không dấu): unaccent + lower contains
    - Có dấu: icontains (case-insensitive exact substring)
    """
    if not keyword:
        return queryset

    keyword_lower = keyword.strip().lower()
    ascii_only = all(ord(ch) < 128 for ch in keyword_lower)

    if ascii_only:
        queryset = queryset.annotate(
            title_unaccent=Lower(
                Func(F("title"), function="unaccent", output_field=TextField())
            ),
            content_unaccent=Lower(
                Func(F("content"), function="unaccent", output_field=TextField())
            ),
            user_full_name_unaccent=Lower(
                Func(
                    F("user__full_name"),
                    function="unaccent",
                    output_field=TextField(),
                )
            ),
            user_email_unaccent=Lower(
                Func(
                    F("user__email"),
                    function="unaccent",
                    output_field=TextField(),
                )
            ),
        )

        return queryset.filter(
            Q(title_unaccent__contains=keyword_lower)
            | Q(content_unaccent__contains=keyword_lower)
            | Q(user_full_name_unaccent__contains=keyword_lower)
            | Q(user_email_unaccent__contains=keyword_lower)
        )

    return queryset.filter(
        Q(title__icontains=keyword)
        | Q(content__icontains=keyword)
        | Q(user__full_name__icontains=keyword)
        | Q(user__email__icontains=keyword)
    )


def apply_sorting(queryset, sort):
    sort_mapping = {
        "newest": "-created_at",
        "oldest": "created_at",
    }
    return queryset.order_by(sort_mapping.get(sort, "-created_at"))
