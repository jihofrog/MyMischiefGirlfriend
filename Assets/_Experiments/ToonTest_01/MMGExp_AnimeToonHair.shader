// Experiment only (ToonTest_01, hair_bob_01): Unity side of the Blender M_hair_bob_01_01 material.
// Vertex colour R = baked AO, G = per-strand random, B = along-strand t. UV.x = across the strand, UV.y = along it.
// Hair colour is a material parameter, separate from the style mesh. Light direction comes from _LightDir.
Shader "MMGExp/AnimeToonHair"
{
    Properties
    {
        _HairColor ("Hair colour", Color) = (0.487, 0.266, 0.233, 1)
        _LightScale ("Lambert scale (Blender sun 3.0)", Float) = 0.76
        _Ambient ("Ambient", Float) = 0.05
        _AOMin ("AO floor", Range(0, 1)) = 0.5
        _EdgeDark ("Edge darkening", Range(0, 1)) = 0.72
        _BandCentre ("Highlight centre along strand", Float) = 0.22
        _BandJitter ("Highlight jitter by strand", Float) = 0.16
        _BandIn ("Highlight inner half width", Float) = 0.008
        _BandOut ("Highlight outer half width", Float) = 0.035
        _BandStrength ("Highlight strength", Range(0, 1)) = 0.5
        _LightDir ("Light direction (world)", Vector) = (-0.3, 0.8, -0.5, 0)
        _OutlineColor ("Outline", Color) = (0.26, 0.12, 0.1, 1)
        _OutlineWidth ("Outline width (m)", Float) = 0.001
    }
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" "RenderType" = "Opaque" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            half4 _HairColor, _OutlineColor;
            float _LightScale, _Ambient, _AOMin, _EdgeDark, _BandCentre, _BandJitter, _BandIn, _BandOut, _BandStrength, _OutlineWidth;
            float4 _LightDir;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "Toon"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct V { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; float3 viewWS : TEXCOORD1; float2 uv : TEXCOORD2; half4 color : COLOR; };
            V vert(A i)
            {
                V o;
                VertexPositionInputs p = GetVertexPositionInputs(i.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.viewWS = GetWorldSpaceViewDir(p.positionWS);
                o.uv = i.uv; o.color = i.color;
                return o;
            }
            float Ramp(float l)
            {
                if (l < 0.30) return 0.5;
                if (l < 0.40) return lerp(0.5, 0.8, (l - 0.30) / 0.10);
                if (l < 0.60) return lerp(0.8, 1.0, (l - 0.40) / 0.20);
                if (l < 0.68) return lerp(1.0, 1.3, (l - 0.60) / 0.08);
                return 1.3;
            }
            half4 frag(V i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                float l = _LightScale * saturate(dot(n, normalize(_LightDir.xyz))) + _Ambient;
                half3 col = _HairColor.rgb * Ramp(l);
                col *= lerp(_AOMin, 1.0, i.color.r);
                float ax = abs(i.uv.x * 2 - 1);
                col = lerp(col, col * _EdgeDark, ax * ax * ax);
                float d = abs(i.uv.y - (_BandCentre + _BandJitter * i.color.g));
                float band = saturate((_BandOut - d) / (_BandOut - _BandIn));
                float cen = saturate((0.85 - ax) / 0.5);
                float lit = saturate((l - 0.40) / 0.20);
                float facing = saturate(dot(n, normalize(i.viewWS)));
                col = lerp(col, lerp(_HairColor.rgb, 1, 0.5), band * cen * lit * facing * _BandStrength);
                return half4(col, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }
            Cull Front
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct A { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct V { float4 positionCS : SV_POSITION; };
            V vert(A i)
            {
                V o;
                float3 ws = TransformObjectToWorld(i.positionOS.xyz) + TransformObjectToWorldNormal(i.normalOS) * _OutlineWidth;
                o.positionCS = TransformWorldToHClip(ws);
                return o;
            }
            half4 frag(V i) : SV_Target { return _OutlineColor; }
            ENDHLSL
        }
    }
}
